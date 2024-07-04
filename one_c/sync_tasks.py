from logging import getLogger

from django.conf import settings
from requests import HTTPError

from absklad_commerce.celery import app
from account.models import DealerStatus, DealerProfile
from one_c.api.clients import OneCAPIClient
from one_c.api.items import DealerItem
from one_c.cache_utils import get_from_cache, send_notif
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

        send_notif(
            form_data_key=form_data_key,
            title=f"Ошибка при попытке создания категории {title}",
            message="Не отвечает 1C-сервер",
            status="failure"
        )
        return
    else:
        form_data["uid"] = category_uid
        Category(**form_data).save()

        send_notif(
            form_data_key=form_data_key,
            title=f"Категория {title} успешно создана",
            message="",
            status="success"
        )


@app.task()
def task_update_category(form_data_key: str):
    form_data = get_from_cache(key=form_data_key)

    if not form_data:
        raise Exception(f"Not found redis key {form_data_key}")

    category_id = form_data.pop("id")  # id on update required!
    new_title = form_data["title"]

    category = Category.objects.get(id=category_id)
    original_title = category.title

    one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
    try:
        one_c.action_category(title=new_title, uid=category.uid, to_delete=False)
    except (HTTPError, KeyError) as e:
        logger.error(e)

        send_notif(
            form_data_key=form_data_key,
            title=f"Ошибка при попытке обновления категории {category.title}",
            message="Не отвечает 1C-сервер",
            status="failure"
        )
        return
    else:
        category.title = new_title
        category.save()
        send_notif(
            form_data_key=form_data_key,
            title="Категория успешно обновлена",
            message=f"{original_title} -> {new_title}",
            status="success"
        )


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
    except (HTTPError, KeyError) as e:
        logger.error(e)

        send_notif(
            form_data_key=form_data_key,
            title=f"Ошибка при попытке обновления продукта {product.title}",
            message="Не отвечает 1C-сервер",
            status="failure"
        )
        return

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
            price = city_price['price']

            product_price = ProductPrice.objects.get(id=city_price['id'])
            product_price.price = price
            to_update.append(product_price)

            for dealer_status in dealer_statuses:
                dealer_price = ProductPrice.objects.filter(
                    city_id=price['city'],
                    product_id=product_id,
                    d_status=dealer_status
                ).first()
                dealer_price.price = calculate_discount(city_price['price'], dealer_status.discount)
                to_update.append(dealer_price)

        if to_update:
            ProductPrice.objects.bulk_update(to_update, ['price'])

    type_prices = form_data.pop("type_prices", None)

    if type_prices:
        to_update = []

        dealer_statuses = DealerStatus.objects.all()
        for price in type_prices:
            price = price['price']

            product_price = ProductPrice.objects.get(id=price['id'])
            product_price.price = price
            to_update.append(product_price)

            for d_status in dealer_statuses:
                dealer_price = ProductPrice.objects.filter(
                    price_type_id=price['price_type'],
                    product_id=product_id,
                    d_status=d_status
                ).first()

                if dealer_price:
                    discount_price = calculate_discount(price, d_status.discount)
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
    send_notif(
        form_data_key=form_data_key,
        title=f"Продукт {product.title} успешно обновлен",
        message="",
        status="success"
    )


# @app.task()
# def task_create_dealer(form_data_key: str):
#     form_data = get_from_cache(key=form_data_key)
#
#     if not form_data:
#         raise Exception(f"Not found redis key {form_data_key}")
#
#     profile = form_data["profile"]
#     profile = DealerProfile.objects.get(id=profile["id"])
#
#     one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
#     try:
#         dealers = (
#             DealerItem(
#                 email=form_data["email"],
#                 name=form_data.get("name", ""),
#                 uid='00000000-0000-0000-0000-000000000000',
#                 phone=form_data.get("phone", ""),
#                 address=profile.get("address", ""),
#                 liability=profile.get("liability", 0),
#                 city_uid=""
#             ),
#         )
#         one_c.action_dealers(
#
#         )
#     except (HTTPError, KeyError) as e:
#         logger.error(e)
#
#         send_notif(
#             form_data_key=form_data_key,
#             title=f"Ошибка при попытке обновления категории {category.title}",
#             message="Не отвечает 1C-сервер",
#             status="failure"
#         )
#         return
#     else:
#         category.title = new_title
#         category.save()
#         send_notif(
#             form_data_key=form_data_key,
#             title="Категория успешно обновлена",
#             message=f"{original_title} -> {new_title}",
#             status="success"
#         )


# order and money doc, inventory, return order


"""
1. Разделить уведомления
2. Задачи
"""