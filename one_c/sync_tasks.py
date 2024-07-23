from decimal import Decimal
from logging import getLogger
from typing import Any

from celery import Task
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from requests import RequestException, ConnectionError, ConnectTimeout, HTTPError

from absklad_commerce.celery import app
from account.models import DealerStatus, DealerProfile, MyUser, BalancePlus, Notification
from account.utils import send_push_notification as mobile_notification
from crm_general.director.utils import create_prod_counts
from crm_general.models import Inventory
from crm_general.tasks import minus_quantity, minus_quantity_order
from crm_general.warehouse_manager.utils import minus_count
from crm_stat.tasks import main_stat_pds_sync, main_stat_order_sync
from general_service.models import Village, Stock, StockPhone
from one_c.api.clients import OneCAPIClient
from one_c.api.items import DealerItem, SaleProductItem, ProductMetaItem
from one_c.cache_utils import get_from_cache, send_web_notif
from one_c.models import MoneyDoc
from order.models import MainOrder, MyOrder, OrderProduct, ReturnOrderProduct
from order.utils import order_total_price, order_cost_price, update_main_order_status
from product.models import Category, AsiaProduct, ProductCount, ProductPrice, ProductCostPrice
from promotion.utils import calculate_discount

logger = getLogger("sync_tasks")

NOTIFY_ERRORS = {
    "default": "Не отвечает 1C-сервер",
    "not_found": "Не найден переданный объект в 1C",
    "bad_request": "Переданные параметры не соответсуют ожиданиям в 1С",
    "key_err": "1С не вернул индентификатор для новой категории",
    "timeout": "Длительное ожидание ответа 1С-сервера",
    "connection_err": "Соединение с 1С-сервером было прервано",
    "req_err": "Ошибка обработки запроса в 1C"
}


class OneCSyncTask(Task):
    typing = False

    def __init__(self, *args, notify_title: str = None, use_key_on_err: list[str] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.notify_title = notify_title
        self.use_key_on_err = use_key_on_err
        self.one_c_client = OneCAPIClient(
            username=settings.ONE_C_USERNAME,
            password=settings.ONE_C_PASSWORD,
            retries=5,
            retries_delay=60,
            retry_force_statuses=[502, 412, 403, 429, 408, 409],
            timeout=60
        )
        self.key = None
        self.form_data = None

    def __call__(self, *args, **kwargs):
        self.key = kwargs.pop("key")
        self.form_data = get_from_cache(key=self.key)

        if not self.form_data:
            raise Exception(f"Not found redis key {self.key} or body is empty")

        if self.use_key_on_err:
            self.notify_title = self.notify_title.format(
                *[self.form_data[key] for key in self.use_key_on_err if key in self.form_data]
            )

        if not self.bind:
            kwargs["one_c"] = self.one_c_client
            kwargs["form_data"] = self.form_data

        try:
            return super().__call__(*args, **kwargs)
        except ConnectTimeout as timeout_exc:
            logger.error(timeout_exc)
            self.send_failure_notify(NOTIFY_ERRORS["timeout"])
        except ConnectionError as con_exc:
            logger.error(con_exc)
            self.send_failure_notify(NOTIFY_ERRORS["connection_err"])
        except (RequestException, HTTPError) as http_exc:
            logger.error(http_exc)

            if http_exc.response:
                logger.error(http_exc.response.body)

            status_code = http_exc.response.status_code if http_exc.response else None
            match status_code:
                case 404:
                    msg = NOTIFY_ERRORS["not_found"]
                case 400:
                    msg = NOTIFY_ERRORS["bad_request"]
                case 500:
                    msg = NOTIFY_ERRORS["req_err"]
                # TODO: handle other error statuses
                case _:
                    msg = NOTIFY_ERRORS["default"]

            self.send_failure_notify(msg)

    def send_failure_notify(self, message) -> None:
        send_web_notif(
            form_data_key=self.key,
            title=self.notify_title,
            status="failure",
            message=message
        )


def _set_attrs_from_dict(obj, data: dict[str, Any]) -> None:
    for field, value in data.items():
        setattr(obj, field, value)


@app.task(
    bind=True,
    base=OneCSyncTask,
    notify_title="Ошибка при попытке создания категории %s",
    use_key_on_err=["title"]
)
def task_create_category(self):
    title = self.form_data["title"]
    response_data = self.one_c_client.action_category(
        title=title,
        uid="00000000-0000-0000-0000-000000000000",
        to_delete=False,
    )
    if 'category_uid' not in response_data:
        self.send_failure_notify(NOTIFY_ERRORS["key_err"])
        return

    self.form_data["uid"] = response_data['category_uid']
    Category(**self.form_data).save()


@app.task(
    bind=True,
    base=OneCSyncTask,
    notify_title="Ошибка при попытке обновления категории #%s",
    use_key_on_err=["title"]
)
def task_update_category(self):
    category_id = self.form_data.pop("id")  # id on update required!
    new_title = self.form_data["title"]

    category = Category.objects.get(id=category_id)
    # successful response expected
    response_data = self.one_c_client.action_category(title=new_title, uid=category.uid, to_delete=False)
    logger.debug(response_data)

    _set_attrs_from_dict(category, self.form_data)
    category.save()


@app.task(
    bind=True,
    base=OneCSyncTask,
    notify_title="Ошибка при попытке обновления продукта #%s",
    use_key_on_err=["id"]
)
def task_update_product(self):
    product_id = self.form_data.pop("id")
    product = AsiaProduct.objects.select_related("category").get(id=product_id)
    category_id = self.form_data.pop("category", None)

    if not category_id:
        category = product.category
    else:
        category = Category.objects.get(id=category_id)
        product.category = category

    # successful response expected
    response_data = self.one_c_client.action_product(
        title=self.form_data.get("title", product.title),
        uid=self.form_data.get("uid", product.uid),
        category_title=category.title,
        category_uid=category.uid,
        to_delete=False,
        vendor_code=self.form_data.get("vendor_code", product.vendor_code)
    )
    logger.debug(response_data)

    with transaction.atomic():
        stocks = {stock["stock_id"]: stock["count_norm"] for stock in self.form_data.pop("stocks", None) or []}
        if stocks:
            to_update = []

            for count_obj in ProductCount.objects.filter(product_id=product_id, stock_id__in=stocks.keys()):
                count_obj.count_norm = stocks[count_obj.stock_id]
                to_update.append(count_obj)

            if to_update:
                ProductCount.objects.bulk_update(to_update, ['count_norm'])

        city_prices = self.form_data.pop("city_prices", None)
        if city_prices:
            to_update = []
            dealer_statuses = DealerStatus.objects.all()

            for city_price in city_prices:
                price = Decimal(city_price['price'])

                product_price = ProductPrice.objects.get(id=city_price['id'])
                product_price.price = price
                to_update.append(product_price)

                for dealer_status in dealer_statuses:
                    dealer_price = ProductPrice.objects.filter(
                        city_id=city_price['city'],
                        product_id=product_id,
                        d_status=dealer_status
                    ).first()
                    dealer_price.price = calculate_discount(
                        price=round(price),
                        discount=dealer_status.discount,
                    )
                    to_update.append(dealer_price)

            if to_update:
                ProductPrice.objects.bulk_update(to_update, ['price'])

        type_prices = self.form_data.pop("type_prices", None)
        if type_prices:
            to_update = []

            dealer_statuses = DealerStatus.objects.all()
            for price_data in type_prices:
                price = Decimal(price_data['price'])

                product_price = ProductPrice.objects.get(id=price_data['id'])
                product_price.price = price
                to_update.append(product_price)

                for d_status in dealer_statuses:
                    dealer_price = ProductPrice.objects.filter(
                        price_type_id=price_data['price_type'],
                        product_id=product_id,
                        d_status=d_status
                    ).first()

                    if dealer_price:
                        discount_price = calculate_discount(
                            price=round(price),
                            discount=d_status.discount,
                        )
                        dealer_price.price = discount_price
                        to_update.append(dealer_price)

            if to_update:
                ProductPrice.objects.bulk_update(to_update, ['price'])

        cost_price = self.form_data.pop("cost_price", None)
        if cost_price:
            cost_price_obj = product.cost_prices.filter(is_active=True).first()

            if cost_price_obj:
                cost_price_obj.price = cost_price
                cost_price_obj.save()
            else:
                ProductCostPrice.objects.create(product=product, price=cost_price, is_active=True)

        _set_attrs_from_dict(product, self.form_data)
        product.save()


@app.task(
    bind=True,
    base=OneCSyncTask,
    notify_title="Ошибка при попытке создания контрагента"
)
def task_create_dealer(self, from_profile: bool = False):
    if from_profile:
        user_data = self.form_data.pop("user")
        profile_data = self.form_data
    else:
        user_data = self.form_data
        profile_data = self.form_data.pop("dealer_profile")

    email = user_data["email"]

    if self.form_data.get("village_id"):
        village = Village.objects.select_related("city").get(id=self.form_data["village_id"])
        city_title = village.city.title
        city_uid = village.city.user_uid
    else:
        city_title = ""
        city_uid = "00000000-0000-0000-0000-000000000000"

    dealers = (
        DealerItem(
            email=email,
            name=user_data.get("name", ""),
            uid='00000000-0000-0000-0000-000000000000',
            phone=user_data.get("phone", ""),
            address=profile_data.get("address", ""),
            liability=profile_data.get("liability", 0),
            city_uid=city_uid,
            city=city_title,
            to_delete=False
        ),
    )
    response_data = self.one_c_client.action_dealers(dealers)

    if "client" not in response_data:
        self.send_failure_notify(NOTIFY_ERRORS["key_err"])
        return

    user_data["uid"] = response_data["client"]
    managers = profile_data.pop("managers", None)

    with transaction.atomic():
        dealer = MyUser.objects.create_user(**user_data)
        profile = DealerProfile.objects.create(user=dealer, **profile_data)

        if managers:
            profile.managers.set(managers)


@app.task(
    bind=True,
    base=OneCSyncTask,
    notify_title="Ошибка при попытке обновления контрагента"
)
def task_update_dealer(self, from_profile: bool = False):
    if from_profile:
        user_data = self.form_data.pop("user", {})
        profile_data = self.form_data

        profile = DealerProfile.objects.get(id=self.form_data.pop("id"))
        user = profile.user
    else:
        profile_data = self.form_data.pop("dealer_profile", {})
        user_data = self.form_data

        user = MyUser.objects.get(id=self.form_data.pop("id"))
        profile = user.dealer_profile

    if profile_data.get("village_id"):
        village = Village.objects.select_related("city").get(id=profile_data["village_id"])
        city_title = village.city.title
        city_uid = village.city.user_uid
    elif profile.village:
        city_title = profile.village.city.title
        city_uid = profile.village.city.user_uid
    else:
        city_title = ""
        city_uid = "00000000-0000-0000-0000-000000000000"

    dealers = (
        DealerItem(
            email=user_data.get("email", user.email),
            name=user_data.get("name", user.name),
            uid=user.uid,
            phone=user_data.get("phone", user.phone),
            address=profile_data.get("address", profile.address),
            liability=profile_data.get("liability", profile.liability),
            city_uid=city_uid,
            city=city_title,
            to_delete=False
        ),
    )
    # successful response expected
    response_data = self.one_c_client.action_dealers(dealers)
    logger.debug(response_data)

    managers = profile_data.pop("managers", None)
    with transaction.atomic():
        _set_attrs_from_dict(profile, profile_data)
        profile.save()

        _set_attrs_from_dict(user, user_data)
        user.save()

        if managers:
            profile.managers.set(managers)


@app.task(
    bind=True,
    base=OneCSyncTask,
    notify_title="Ошибка модерации заявки на полнение баланса #%s",
    use_key_on_err=["balance_id"]
)
def task_balance_plus_moderation(self):
    balance_id = self.form_data["balance_id"]
    is_success = self.form_data["is_success"]
    status = self.form_data['status']

    balance = BalancePlus.objects.filter(is_moderation=False, id=balance_id).first()
    if not balance:
        if BalancePlus.objects.filter(is_moderation=True, id=balance_id).exists():
            self.send_failure_notify(NOTIFY_ERRORS["key_err"])
        else:
            self.send_failure_notify(NOTIFY_ERRORS["key_err"])
        return

    balance.is_moderation = True
    balance.is_success = is_success
    if not is_success:
        balance.save()
        mobile_notification(
            text="Заявка на пополнение отклонена.",
            title=f"Заявка на пополнение #{balance_id}",
            tokens=[balance.dealer.user.firebase_token],
            link_id=balance_id,
            status="balance",
        )
        return

    stock = balance.dealer.village.city.stocks.first()
    money_doc = MoneyDoc(
        status=status,
        user=balance.dealer.user,
        amount=balance.amount,
        cash_box=stock.cash_box if stock else None,
        created_at=timezone.now()
    )

    try:
        if 'Нал' == money_doc.status:
            order_type = 'Наличка'
            cash_box_uid = money_doc.cash_box.uid
        else:
            order_type = 'Без нал'
            cash_box_uid = ''
    except AttributeError as exc:
        self.send_failure_notify("Не найдена касса")
        raise exc

    payload = self.one_c_client.action_money_doc(
        user_uid=balance.dealer.user.uid,
        amount=int(balance.amount),
        created_at=f'{timezone.localtime(money_doc.created_at)}',
        order_type=order_type,
        cashbox_uid=cash_box_uid,
        to_delete=False,
        uid="00000000-0000-0000-0000-000000000000"
    )
    if "result_uid" not in payload:
        self.send_failure_notify(NOTIFY_ERRORS["key_err"])
        return

    money_doc.uid = payload["result_uid"]

    with transaction.atomic():
        balance.save()
        money_doc.save()

    mobile_notification(
        text="Заявка на пополнение одобрена!",
        title=f"Заявка на пополнение #{balance_id}",
        tokens=[balance.dealer.user.firebase_token],
        link_id=balance_id,
        status="balance",
    )
    # stats
    main_stat_pds_sync(money_doc)
    money_doc.is_checked = True
    money_doc.save()


@app.task(
    bind=True,
    base=OneCSyncTask,
    notify_title="Ошибка модерации оплаты заказа #%s",
    use_key_on_err=["order_id"]
)
def task_order_paid_moderation(self):
    order_id = self.form_data["order_id"]
    order = MainOrder.objects.get(id=order_id)
    order.status = self.form_data["status"]

    if order.status != "paid":
        order.save()
        mobile_notification(
            tokens=[order.author.user.firebase_token],
            title=f"Заказ #{order_id}",
            text="Ваша оплата заказа не успешна.",
            link_id=order_id,
            status="order"
        )
        Notification.objects.create(
            user=order.author.user,
            title=f'Заказ #{order.id}',
            link_id=order_id,
            status='order'
        )
        return

    if order.type_status in ("cash", "kaspi"):
        type_status = 'Наличка'
        create_type_status = 'Нал'
        cash_box_uid = order.stock.cash_box.uid
    else:
        type_status = 'Без нал'
        cash_box_uid = ''
        create_type_status = 'Без нал'

    response_data = self.one_c_client.action_money_doc(
        user_uid=order.author.user.uid,
        amount=int(order.price),
        created_at=f"{timezone.localtime(order.created_at)}",
        order_type=type_status,
        cashbox_uid=cash_box_uid,
        to_delete=False,
        uid="00000000-0000-0000-0000-000000000000"
    )
    if 'result_uid' not in response_data:
        self.send_failure_notify(NOTIFY_ERRORS["key_err"])
        return

    order.payment_doc_uid = response_data['result_uid']
    with transaction.atomic():
        order.paid_at = timezone.make_aware(timezone.localtime().now())
        order.save()
        minus_quantity(order.id, order.stock.id)
        money_doc = MoneyDoc.objects.create(
            user=order.author.user,
            amount=order.price,
            uid=order.payment_doc_uid,
            cash_box=order.stock.cash_box,
            status=create_type_status
        )

    mobile_notification(
        tokens=[order.author.user.firebase_token],
        title=f"Заказ #{order_id}",
        text="Ваша оплата заказа не успешна.",
        link_id=order_id,
        status="order"
    )
    Notification.objects.create(
        user=order.author.user,
        title=f'Заказ #{order.id}',
        link_id=order_id,
        status='order'
    )

    # stats
    main_stat_pds_sync(money_doc)
    money_doc.is_checked = True
    money_doc.save()


@app.task(
    bind=True,
    base=OneCSyncTask,
    notify_title="Ошибка отгрузки заказа #%s",
    use_key_on_err=["order_id"]
)
def task_order_partial_sent(self):
    order_id = self.form_data['order_id']
    products_data = self.form_data['products']
    wh_stock_id = self.form_data.pop("wh_stock_id")

    main_order = MainOrder.objects.select_related("author", "stock").get(id=order_id)
    product_objs = AsiaProduct.objects.filter(id__in=[key for key in products_data])
    released_at = timezone.localtime().now()

    order_products_data = []
    for product_obj in product_objs:
        price_type = main_order.author.price_type
        dealer = main_order.author

        if price_type:
            prod_price_obj = (
                dealer.user.discount_prices.filter(
                    is_active=True,
                    product=product_obj,
                    price_type=price_type
                ).first()
                or
                product_obj.prices.filter(
                    price_type=price_type,
                    d_status=main_order.author.dealer_status
                ).first()
            )
        else:
            prod_price_obj = (
                dealer.user.discount_prices.filter(
                    is_active=True,
                    product=product_obj,
                    city=main_order.author.price_city
                ).first()
                or
                product_obj.prices.filter(
                    city=main_order.author.price_city,
                    d_status=main_order.author.dealer_status
                ).first()
            )

        try:
            prod_price = prod_price_obj.price
            discount_amount = prod_price_obj.old_price - prod_price
        except AttributeError as exc:
            self.send_failure_notify(f"Не найдена цена для товара #{product_obj.id}")
            raise exc

        sale_count = products_data[str(product_obj.id)]
        order_products_data.append(
            {
                "ab_product": product_obj,
                "count": sale_count,
                "price": prod_price,
                "total_price": sale_count * prod_price,
                "discount": discount_amount
            }
        )

    response_data = self.one_c_client.action_sale(
        user_uid=main_order.author.user.uid,
        created_at=f'{released_at}',
        payment_doc_uid=main_order.payment_doc_uid,
        city_uid=main_order.stock.uid,
        to_delete=False,
        uid='00000000-0000-0000-0000-000000000000',
        products=(
            SaleProductItem(
                title=p_data["ab_product"].title,
                uid=p_data["ab_product"].uid,
                count=int(p_data["count"]),
                price=int(p_data["price"])
            ) for p_data in order_products_data
        )
    )

    if 'result_uid' not in response_data:
        self.send_failure_notify(NOTIFY_ERRORS["key_err"])
        return

    with transaction.atomic():
        order = MyOrder.objects.create(
            uid=response_data['result_uid'],
            price=order_total_price(product_objs, products_data, main_order.author),
            cost_price=order_cost_price(product_objs, products_data),
            main_order_id=order_id,
            author=main_order.author,
            stock=main_order.stock,
            status="sent",
            type_status=main_order.type_status,
            created_at=main_order.created_at,
            released_at=timezone.make_aware(timezone.localtime().now()),
            paid_at=main_order.paid_at,
        )
        OrderProduct.objects.bulk_create([OrderProduct(order=order, **p_data) for p_data in order_products_data])

        minus_count(main_order, order_products_data)
        update_main_order_status(main_order)

    mobile_notification(
        tokens=[main_order.author.user.firebase_token],
        title=f"Заказ #{order_id}",
        text="Ваш заказ отгружен!",
        link_id=order_id,
        status="order"
    )

    # stats
    main_stat_order_sync(order)
    order.order_products.update(is_checked=True)
    minus_quantity_order(order.id, wh_stock_id)


@app.task(
    bind=True,
    base=OneCSyncTask,
    notify_title="Ошибка при попытке создания склада"
)
def task_create_stock(self):
    response_data = self.one_c_client.action_stock(
        uid="",
        title=self.form_data.get("title", ""),
        to_delete=False
    )

    if 'result_uid' not in response_data:
        self.send_failure_notify(NOTIFY_ERRORS["key_err"])
        return

    self.form_data["uid"] = response_data['result_uid']
    phones = self.form_data.pop("phones", None)

    with transaction.atomic():
        stock = Stock.objects.create(**self.form_data)
        if phones:
            StockPhone.objects.bulk_create([StockPhone(stock=stock, phone=data['phone']) for data in phones])
        create_prod_counts(stock)


@app.task(
    bind=True,
    base=OneCSyncTask,
    notify_title="Ошибка при попытке обновления склада #%s",
    use_key_on_err=["id"]
)
def task_update_stock(self):
    stock_id = self.form_data.pop("id")
    stock_obj = Stock.objects.get(id=stock_id)

    # successfully response status excepted
    response_data = self.one_c_client.action_stock(
        uid=stock_obj.uid,
        title=self.form_data.get("title", stock_obj.title),
        to_delete=False
    )
    logger.debug(response_data)

    phones = self.form_data.pop("phones", None)

    with transaction.atomic():
        _set_attrs_from_dict(stock_obj, self.form_data)
        stock_obj.save()

        if phones:
            stock_obj.phones.all().delete()
            StockPhone.objects.bulk_create([StockPhone(stock=stock_obj, phone=data['phone']) for data in phones])


@app.task(
    bind=True,
    base=OneCSyncTask,
    notify_title="Ошибка при попытке обновления инвентаря #%s",
    use_key_on_err=["id"]
)
def task_inventory_update(self):
    inventory_id = self.form_data.pop("id")
    inventory_obj = Inventory.objects.get(id=inventory_id)

    _set_attrs_from_dict(inventory_obj, self.form_data)

    if self.form_data.get("status", "") != "moderated" or inventory_obj.status != "moderated":
        inventory_obj.save()
        return

    if inventory_obj.sender and inventory_obj.sender.warehouse_profile:
        stock = inventory_obj.sender.warehouse_profile.stock
        stock_uid = "" if not stock else stock.uid
    else:
        stock_uid = ""

    response_data = self.one_c_client.action_inventory(
        uid=inventory_obj.uid,
        user_uid='fcac9f0f-34d2-11ed-8a2f-2c59e53ae4c3',
        to_delete=False,
        created_at=f'{timezone.localtime(inventory_obj.created_at)}',
        city_uid=stock_uid,
        products=(
            ProductMetaItem(
                product_uid=p.product.uid,
                count=p.count,
                use_prod_uid=True
            ) for p in inventory_obj.products.all()
        )
    )
    if 'result_uid' not in response_data:
        self.send_failure_notify(NOTIFY_ERRORS["key_err"])
        return

    inventory_obj.uid = response_data['result_uid']
    inventory_obj.save()


@app.task(
    bind=True,
    base=OneCSyncTask,
    notify_title="Ошибка при попытке обновления возрата #%s",
    use_key_on_err=["id"]
)
def task_update_return_order(self):
    return_product_id = self.form_data.pop("id")
    return_product_obj = ReturnOrderProduct.objects.select_related("return_order", "product").get(id=return_product_id)
    status = self.form_data.get("status", "")
    return_order_obj = return_product_obj.return_order
    order_obj = return_order_obj.order

    if status != "success" or return_product_obj.status != "success":
        for field, value in self.form_data.items():
            setattr(return_product_obj, field, value)

        return_product_obj.save()
        return

    # TODO: save Return order uid from response data
    response_data = self.one_c_client.action_return_order(
        uid=return_order_obj.order.uid,
        return_uid=return_order_obj.uid,
        to_delete=False,
        created_at=f'{timezone.localtime(return_order_obj.created_at)}',
        products=(
            ProductMetaItem(
                product_uid=p.product.uid,
                count=int(p.count),
                use_prod_uid=False
            ) for p in return_order_obj.products.all()
        )
    )
    logger.debug(response_data)

    with transaction.atomic():
        order_product = OrderProduct.objects.get(
            order=order_obj,
            ab_product_id=return_product_obj.product.id
        )
        product_count = order_product.count
        product_price = order_product.price
        deducted = product_count - return_product_obj.count

        if deducted <= 0:
            order_product.delete()
        else:
            order_product.count -= return_product_obj.count
            order_product.price = (order_product.count - return_product_obj.count) * product_price
            order_product.save()

        total_order_price = sum(order_obj.order_products.filter().values_list('total_price', flat=True))
        order_obj.price = total_order_price
        order_obj.save()

        _set_attrs_from_dict(return_product_obj, self.form_data)
        return_product_obj.save()
