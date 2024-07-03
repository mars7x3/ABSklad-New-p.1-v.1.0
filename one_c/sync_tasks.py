from logging import getLogger

from django.conf import settings
from requests import HTTPError

from absklad_commerce.celery import app
from account.models import DealerStatus
from notification.utils import send_web_push_notification
from one_c.api.clients import OneCAPIClient
from one_c.cache_utils import get_form_data_from_cache, rebuild_cache_key
from product.models import Category, AsiaProduct, ProductCount, ProductPrice, ProductCostPrice
from promotion.utils import calculate_discount

logger = getLogger("sync_tasks")


@app.task()
def task_create_category(form_data_key: str):
    form_data = get_form_data_from_cache(key=form_data_key)
    key_meta = rebuild_cache_key(key=form_data_key)
    user_id, action = key_meta["user_id"], key_meta["action"]

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

        send_web_push_notification(
            user_id=user_id,
            title=f"Ошибка при попытке создания категории {title}",
            msg="Не отвечает 1C-сервер",
            data={
                "task_id": form_data_key,
                "open_url": settings.ONE_C_TASK_URL % form_data_key
            },
            message_type="task_message",
        )
        return
    else:
        form_data["uid"] = category_uid
        Category(**form_data).save()

        send_web_push_notification(user_id=user_id, title=f"Категория {title} успешно создана")


@app.task()
def task_update_category(form_data_key: str):
    form_data = get_form_data_from_cache(key=form_data_key)
    key_meta = rebuild_cache_key(key=form_data_key)
    user_id, action = key_meta["user_id"], key_meta["action"]

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

        send_web_push_notification(
            user_id=user_id,
            title=f"Ошибка при попытке обновления категории {category.title}",
            msg="Не отвечает 1C-сервер",
            data={
                "task_id": form_data_key,
                "open_url": settings.ONE_C_TASK_URL % form_data_key
            },
            message_type="task_message",
        )
        return
    else:
        category.title = new_title
        category.save()

        send_web_push_notification(
            user_id=user_id,
            title="Категория успешно обновлена",
            msg=f"{original_title} -> {new_title}"
        )


@app.task()
def task_delete_category(form_data_key: str):
    form_data = get_form_data_from_cache(key=form_data_key)
    key_meta = rebuild_cache_key(key=form_data_key)
    user_id, _ = key_meta["user_id"], key_meta["action"]

    if not form_data:
        raise Exception(f"Not found redis key {form_data_key}")

    category_id = form_data.pop("id")  # id on update required!
    category = Category.objects.get(id=category_id)
    title = category.title

    one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
    try:
        one_c.action_category(title=category.title, uid=category.uid, to_delete=True)
    except (HTTPError, KeyError) as e:
        logger.error(e)

        send_web_push_notification(
            user_id=user_id,
            title=f"Ошибка при попытке удалении категории {title}",
            msg="Не отвечает 1C-сервер",
            data={
                "task_id": form_data_key,
                "open_url": settings.ONE_C_TASK_URL % form_data_key
            },
            message_type="task_message",
        )
        return
    else:
        category.delete()
        send_web_push_notification(user_id=user_id, title=f"Категория {title} успешно удалена")


@app.task()
def task_update_product(form_data_key: str):
    form_data = get_form_data_from_cache(key=form_data_key)
    key_meta = rebuild_cache_key(key=form_data_key)
    user_id, _ = key_meta["user_id"], key_meta["action"]

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

        send_web_push_notification(
            user_id=user_id,
            title=f"Ошибка при попытке обновления продукта {product.title}",
            msg="Не отвечает 1C-сервер",
            data={
                "task_id": form_data_key,
                "open_url": settings.ONE_C_TASK_URL % form_data_key
            },
            message_type="task_message",
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
    send_web_push_notification(user_id=user_id, title=f"Продукт {product.title} успешно обновлен")


@app.task()
def task_delete_product(form_data_key: str):
    form_data = get_form_data_from_cache(key=form_data_key)
    key_meta = rebuild_cache_key(key=form_data_key)
    user_id, _ = key_meta["user_id"], key_meta["action"]

    if not form_data:
        raise Exception(f"Not found redis key {form_data_key}")

    product_id = form_data["id"]
    product = AsiaProduct.objects.select_related("category").get(id=product_id)

    one_c = OneCAPIClient(username=settings.ONE_C_USERNAME, password=settings.ONE_C_PASSWORD)
    try:
        one_c.action_product(
            title=product.title,
            uid=product.uid,
            category_title=product.category.title,
            category_uid=product.category.uid,
            to_delete=True,
            vendor_code=product.vendor_code
        )
    except (HTTPError, KeyError) as e:
        logger.error(e)

        send_web_push_notification(
            user_id=user_id,
            title=f"Ошибка при попытке удаления продукта {product.title}",
            msg="Не отвечает 1C-сервер",
            data={
                "task_id": form_data_key,
                "open_url": settings.ONE_C_TASK_URL % form_data_key
            },
            message_type="task_message",
        )
        return

    product.delete()
    send_web_push_notification(user_id=user_id, title=f"Продукт {product.title} успешно удален")
