from decimal import Decimal
from logging import getLogger

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from requests import HTTPError

from absklad_commerce.celery import app
from account.models import DealerStatus, DealerProfile, MyUser, BalancePlus, Notification
from account.utils import send_push_notification
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


@app.task()
def task_create_category(form_data_key: str):
    form_data = get_from_cache(key=form_data_key)

    if not form_data:
        raise Exception(f"Not found redis key {form_data_key}")

    title = form_data["title"]
    one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
    try:
        response_data = one_c.action_category(
            title=title,
            uid="00000000-0000-0000-0000-000000000000",
            to_delete=False,
        )
        category_uid = response_data['category_uid']
    except (HTTPError, KeyError) as e:
        logger.error(e)

        send_web_notif(
            form_data_key=form_data_key,
            title=f"Ошибка при попытке создания категории {title}",
            message="Не отвечает 1C-сервер",
            status="failure"
        )
        return
    else:
        form_data["uid"] = category_uid
        Category(**form_data).save()


@app.task()
def task_update_category(form_data_key: str):
    form_data = get_from_cache(key=form_data_key)

    if not form_data:
        raise Exception(f"Not found redis key {form_data_key}")

    category_id = form_data.pop("id")  # id on update required!
    new_title = form_data["title"]

    category = Category.objects.get(id=category_id)
    one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
    try:
        one_c.action_category(title=new_title, uid=category.uid, to_delete=False)
    except HTTPError as e:
        logger.error(e)

        send_web_notif(
            form_data_key=form_data_key,
            title=f"Ошибка при попытке обновления категории {category.title}",
            message="Не отвечает 1C-сервер",
            status="failure"
        )
        return
    else:
        for field, value in form_data.items():
            setattr(category, field, value)
        category.save()


@app.task()
def task_update_product(form_data_key: str):
    form_data = get_from_cache(key=form_data_key)

    if not form_data:
        raise Exception(f"Not found redis key {form_data_key}")

    product_id = form_data.pop("id")
    product = AsiaProduct.objects.select_related("category").get(id=product_id)
    category_id = form_data.pop("category", None)

    if not category_id:
        category = product.category
    else:
        category = Category.objects.get(id=category_id)
        product.category = category

    one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
    try:
        one_c.action_product(
            title=form_data.get("title", product.title),
            uid=form_data.get("uid", product.uid),
            category_title=category.title,
            category_uid=category.uid,
            to_delete=False,
            vendor_code=form_data.get("vendor_code", product.vendor_code)
        )
    except HTTPError as e:
        logger.error(e)

        send_web_notif(
            form_data_key=form_data_key,
            title=f"Ошибка при попытке обновления продукта {product.title}",
            message="Не отвечает 1C-сервер",
            status="failure"
        )
        return

    with transaction.atomic():
        stocks = {stock["stock_id"]: stock["count_norm"] for stock in form_data.pop("stocks", None) or []}
        if stocks:
            to_update = []

            for count_obj in ProductCount.objects.filter(product_id=product_id, stock_id__in=stocks.keys()):
                count_obj.count_norm = stocks[count_obj.stock_id]
                to_update.append(count_obj)

            if to_update:
                ProductCount.objects.bulk_update(to_update, ['count_norm'])

        city_prices = form_data.pop("city_prices", None)
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

        type_prices = form_data.pop("type_prices", None)
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

        cost_price = form_data.pop("cost_price", None)
        if cost_price:
            cost_price_obj = product.cost_prices.filter(is_active=True).first()

            if cost_price_obj:
                cost_price_obj.price = cost_price
                cost_price_obj.save()
            else:
                ProductCostPrice.objects.create(product=product, price=cost_price, is_active=True)

        for field, value in form_data.items():
            setattr(product, field, value)
        product.save()


@app.task()
def task_create_dealer(form_data_key: str, from_profile: bool = False):
    form_data = get_from_cache(key=form_data_key)

    if not form_data:
        raise Exception(f"Not found redis key {form_data_key}")

    if from_profile:
        user_data = form_data.pop("user")
        profile_data = form_data
    else:
        user_data = form_data
        profile_data = form_data.pop("dealer_profile")

    email = user_data["email"]

    if form_data.get("village_id"):
        village = Village.objects.select_related("city").get(id=form_data["village_id"])
        city_title = village.city.title
        city_uid = village.city.user_uid
    else:
        city_title = ""
        city_uid = "00000000-0000-0000-0000-000000000000"

    one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
    try:
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
        response_data = one_c.action_dealers(dealers)
        user_data["uid"] = response_data["client"]
    except (HTTPError, KeyError) as e:
        logger.error(e)

        send_web_notif(
            form_data_key=form_data_key,
            title=f"Ошибка при попытке создания клиента {email}",
            message="Не отвечает 1C-сервер",
            status="failure"
        )
        return
    else:
        managers = profile_data.pop("managers", None)

        with transaction.atomic():
            dealer = MyUser.objects.create_user(**user_data)
            profile = DealerProfile.objects.create(user=dealer, **profile_data)

            if managers:
                profile.managers.set(managers)


@app.task()
def task_update_dealer(form_data_key: str, from_profile: bool = False):
    form_data = get_from_cache(key=form_data_key)

    if not form_data:
        raise Exception(f"Not found redis key {form_data_key}")

    if from_profile:
        user_data = form_data.pop("user", {})
        profile_data = form_data

        profile = DealerProfile.objects.get(id=form_data.pop("id"))
        user = profile.user
    else:
        profile_data = form_data.pop("dealer_profile", {})
        user_data = form_data

        user = MyUser.objects.get(id=form_data.pop("id"))
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

    one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
    try:
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
        one_c.action_dealers(dealers)
    except HTTPError as e:
        logger.error(e)

        send_web_notif(
            form_data_key=form_data_key,
            title=f"Ошибка при попытке обновления клиента {user.email}",
            message="Не отвечает 1C-сервер",
            status="failure"
        )
        return

    managers = profile_data.pop("managers", None)

    with transaction.atomic():
        for field, value in profile_data.items():
            setattr(profile, field, value)

        for field, value in user_data.items():
            setattr(user, field, value)

        profile.save()
        user.save()

        if managers:
            profile.managers.set(managers)


@app.task()
def task_balance_plus_moderation(form_data_key: str):
    form_data = get_from_cache(key=form_data_key)

    if not form_data:
        raise Exception(f"Not found redis key {form_data_key}")

    balance_id = form_data["balance_id"]
    is_success = form_data["is_success"]
    status = form_data['status']

    balance = BalancePlus.objects.filter(is_moderation=False, id=balance_id).first()
    if not balance:
        send_web_notif(
            form_data_key=form_data_key,
            title=f"Ошибка модерации заявки на полнение баланса #{balance_id}",
            message="Не найден счет или он ранее уже был обработан",
            status="error"
        )
        return

    balance.is_moderation = True
    balance.is_success = is_success
    if not is_success:
        balance.save()
        send_push_notification(
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

    one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
    try:
        if 'Нал' == money_doc.status:
            order_type = 'Наличка'
            cash_box_uid = money_doc.cash_box.uid
        else:
            order_type = 'Без нал'
            cash_box_uid = ''

        payload = one_c.action_money_doc(
            user_uid=balance.dealer.user.uid,
            amount=int(balance.amount),
            created_at=f'{timezone.localtime(money_doc.created_at)}',
            order_type=order_type,
            cashbox_uid=cash_box_uid,
            to_delete=False,
            uid="00000000-0000-0000-0000-000000000000"
        )
        money_doc.uid = payload["result_uid"]
    except (HTTPError, KeyError) as e:
        logger.error(e)

        send_web_notif(
            form_data_key=form_data_key,
            title=f"Ошибка модерации заявки на полнение баланса #{balance_id}",
            message="Не отвечает 1C-сервер",
            status="failure"
        )
        return
    except AttributeError as e:
        logger.error(e)

        send_web_notif(
            form_data_key=form_data_key,
            title=f"Ошибка модерации заявки на полнение баланса #{balance_id}",
            message="Не найдена касса",
            status="failure"
        )
        return

    with transaction.atomic():
        balance.save()
        money_doc.save()
        main_stat_pds_sync(money_doc)
        money_doc.is_checked = True
        money_doc.save()

    send_push_notification(
        text="Заявка на пополнение одобрена!",
        title=f"Заявка на пополнение #{balance_id}",
        tokens=[balance.dealer.user.firebase_token],
        link_id=balance_id,
        status="balance",
    )


@app.task()
def task_order_paid_moderation(form_data_key: str):
    form_data = get_from_cache(key=form_data_key)
    if not form_data:
        raise Exception(f"Not found redis key {form_data_key}")

    order_id = form_data["order_id"]
    order = MainOrder.objects.get(id=order_id)
    order.status = form_data["status"]

    if order.status != "paid":
        order.save()
        send_push_notification(
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

    one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
    try:
        response_data = one_c.action_money_doc(
            user_uid=order.author.user.uid,
            amount=int(order.price),
            created_at=f"{timezone.localtime(order.created_at)}",
            order_type=type_status,
            cashbox_uid=cash_box_uid,
            to_delete=False,
            uid="00000000-0000-0000-0000-000000000000"
        )
        order.payment_doc_uid = response_data['result_uid']
    except (HTTPError, KeyError) as e:
        logger.error(e)

        send_web_notif(
            form_data_key=form_data_key,
            title=f"Ошибка оплаты заказа #{order_id}",
            message="Не отвечает 1C-сервер",
            status="failure"
        )
        return
    else:
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
            main_stat_pds_sync(money_doc)
            money_doc.is_checked = True
            money_doc.save()

        send_push_notification(
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


@app.task()
def task_order_partial_sent(form_data_key: str):
    form_data = get_from_cache(key=form_data_key)
    if not form_data:
        raise Exception(f"Not found redis key {form_data_key}")

    order_id = form_data['order_id']
    products_data = form_data['products']
    wh_stock_id = form_data.pop("wh_stock_id")

    main_order = MainOrder.objects.select_related("author", "stock").get(id=order_id)
    product_objs = AsiaProduct.objects.filter(id__in=[key for key in products_data])
    released_at = timezone.localtime().now()

    order_products_data = []
    for product_obj in product_objs:
        try:
            prod_price = (
                product_obj.prices.filter(
                    price_type=main_order.author.price_type,
                    d_status=main_order.author.dealer_status
                ).first()
                or
                product_obj.prices.filter(
                    city=main_order.author.price_city,
                    d_status=main_order.author.dealer_status
                ).first()
            ).price
        except AttributeError as e:
            logger.error(e)

            send_web_notif(
                form_data_key=form_data_key,
                title=f"Ошибка отгрузки заказа #{order_id}",
                message=f"Не найдена цена для товара {product_obj.title}",
                status="failure"
            )
            return

        order_products_data.append(
            {
                "ab_product": product_obj,
                "count": products_data[str(product_obj.id)],
                "price": prod_price,
            }
        )

    one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
    try:
        response_data = one_c.action_sale(
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
    except HTTPError as e:
        logger.error(e)

        send_web_notif(
            form_data_key=form_data_key,
            title=f"Ошибка отгрузки заказа #{order_id}",
            message="Не отвечает 1C-сервер",
            status="failure"
        )
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

    with transaction.atomic():
        minus_count(main_order, order_products_data)
        update_main_order_status(main_order)
        main_stat_order_sync(order)
        order.order_products.update(is_checked=True)
        minus_quantity_order(order.id, wh_stock_id)

    send_push_notification(
        tokens=[main_order.author.user.firebase_token],
        title=f"Заказ #{order_id}",
        text="Ваш заказ отгружен!",
        link_id=order_id,
        status="order"
    )


@app.task()
def task_create_stock(form_data_key: str):
    form_data = get_from_cache(key=form_data_key)
    if not form_data:
        raise Exception(f"Not found redis key {form_data_key}")

    phones = form_data.pop("phones", None)
    one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
    try:
        response_data = one_c.action_stock(
            uid="",
            title=form_data.get("title", ""),
            to_delete=False
        )
        form_data["uid"] = response_data['result_uid']
    except (HTTPError, KeyError) as e:
        logger.error(e)

        send_web_notif(
            form_data_key=form_data_key,
            title="Ошибка при попытке создания склада",
            message="Не отвечает 1C-сервер",
            status="failure"
        )
        return

    with transaction.atomic():
        stock = Stock.objects.create(**form_data)
        if phones:
            StockPhone.objects.bulk_create([StockPhone(stock=stock, phone=data['phone']) for data in phones])
        create_prod_counts(stock)


@app.task()
def task_update_stock(form_data_key: str):
    form_data = get_from_cache(key=form_data_key)
    if not form_data:
        raise Exception(f"Not found redis key {form_data_key}")

    stock_id = form_data.pop("id")
    phones = form_data.pop("phones", None)
    stock_obj = Stock.objects.get(id=stock_id)

    one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
    try:
        one_c.action_stock(
            uid=stock_obj.uid,
            title=form_data.get("title", stock_obj.title),
            to_delete=False
        )
    except (HTTPError, KeyError) as e:
        logger.error(e)

        send_web_notif(
            form_data_key=form_data_key,
            title="Ошибка при попытке обновления склада",
            message="Не отвечает 1C-сервер",
            status="failure"
        )
        return

    for field, value in form_data.items():
        setattr(stock_obj, field, value)

    with transaction.atomic():
        stock_obj.save()

        if phones:
            stock_obj.phones.all().delete()
            StockPhone.objects.bulk_create([StockPhone(stock=stock_obj, phone=data['phone']) for data in phones])


@app.task()
def task_inventory_update(form_data_key: str):
    form_data = get_from_cache(key=form_data_key)
    if not form_data:
        raise Exception(f"Not found redis key {form_data_key}")

    inventory_id = form_data.pop("id")
    inventory_obj = Inventory.objects.get(id=inventory_id)

    for field, value in form_data.items():
        setattr(inventory_obj, field, value)

    if form_data.get("status", "") != "moderated" or inventory_obj.status != "moderated":
        inventory_obj.save()
        return

    if inventory_obj.sender and inventory_obj.sender.warehouse_profile:
        stock = inventory_obj.sender.warehouse_profile.stock
        stock_uid = "" if not stock else stock.uid
    else:
        stock_uid = ""

    one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
    try:
        response_data = one_c.action_inventory(
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
        inventory_obj.uid = response_data['result_uid']
    except (HTTPError, KeyError) as e:
        logger.error(e)

        send_web_notif(
            form_data_key=form_data_key,
            title=f"Ошибка при попытке обновления инвентаря #{inventory_obj.id}",
            message="Не отвечает 1C-сервер",
            status="failure"
        )
        return
    else:
        inventory_obj.save()


@app.task()
def task_update_return_order(form_data_key: str):
    form_data = get_from_cache(key=form_data_key)
    if not form_data:
        raise Exception(f"Not found redis key {form_data_key}")

    return_product_id = form_data.pop("id")
    return_product_obj = ReturnOrderProduct.objects.select_related("return_order", "product").get(id=return_product_id)
    status = form_data.get("status", "")
    return_order_obj = return_product_obj.return_order
    order_obj = return_order_obj.order

    if status != "success" or return_product_obj.status != "success":
        for field, value in form_data.items():
            setattr(return_product_obj, field, value)

        return_product_obj.save()
        return

    one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
    try:
        one_c.action_return_order(
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
    except (HTTPError, KeyError) as e:
        logger.error(e)

        send_web_notif(
            form_data_key=form_data_key,
            title=f"Ошибка при попытке обновления возрата #{order_obj.id}",
            message="Не отвечает 1C-сервер",
            status="failure"
        )
        return

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

        for field, value in form_data.items():
            setattr(return_product_obj, field, value)

        return_product_obj.save()
