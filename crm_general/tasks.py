import datetime
import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Q
from django.utils.timezone import now

from absklad_commerce.celery import app
from account.models import DealerStatus, DealerProfile
from crm_general.models import DealerKPIPlan, CityProductToBuy, ProductToBuy, DealerKPIPlanStat, CityProductToBuyStat
from crm_general.utils import collect_orders_data_for_kpi_plan, round_up
from general_service.models import Stock
from one_c.models import MoneyDoc
from order.models import MyOrder, OrderProduct, MainOrder
from product.models import ProductCount, ProductPrice
from promotion.models import Discount

logger = logging.getLogger('tasks_management')


@app.task
def minus_quantity(order_id, stock_id):
    order = MainOrder.objects.get(id=order_id)
    stock = Stock.objects.get(id=stock_id)
    products_id = order.products.all().values_list('ab_product_id', 'count')
    counts = ProductCount.objects.filter(stock=stock)
    for p_id, count in products_id:
        quantity = counts.get(product_id=p_id)
        quantity.count_crm -= count
        quantity.save()


@app.task()
def create_dealer_kpi_for_this_month():
    today = now()
    target_month, target_year = today.month, today.year
    months_ago = settings.KPI_CHECK_MONTHS
    increase_threshold = settings.KPI_INCREASE_THRESHOLD

    new_plans = []
    processed_dealer_ids = set()
    collected_products_to_buy = {}
    collected_product_counts = {}

    logger.info(f"Start creating `DealerKPIPlan` for month {target_month} and year {target_year}...")
    logger.debug(f"Checking orders {months_ago} months with an increase option {increase_threshold * 100}%")

    orders = collect_orders_data_for_kpi_plan(check_months_ago=months_ago, increase_threshold=increase_threshold)
    saved_dealer_ids = DealerKPIPlan.objects.filter(
        target_month=target_month,
        created_at__year=target_year
    ).values_list("dealer_id", flat=True)

    for order in orders:
        dealer_id = order["dealer_id"]

        if dealer_id in saved_dealer_ids:
            logger.warning(f"`DealerKPIPlan` for user with id {dealer_id} was saved and will be passed")
            continue

        if dealer_id not in processed_dealer_ids:
            new_plan = DealerKPIPlan(
                dealer_id=dealer_id,
                target_month=target_month,
                spend_amount=order["spend_amount"]
            )
            logger.debug(f"User with id {dealer_id} will be added to create `DealerKPIPlan`")
            new_plans.append(new_plan)

        product_id = order["product_id"]
        if dealer_id not in collected_products_to_buy:
            collected_products_to_buy[dealer_id] = []

        collected_products_to_buy[dealer_id].append(product_id)

        if product_id not in collected_product_counts:
            collected_product_counts[product_id] = []

        avg_count = order["avg_count"]
        count = int(round_up(avg_count + avg_count * increase_threshold))

        city_count = dict(city_id=order["city_id"], count=count)
        collected_product_counts[product_id].append(city_count)
        logger.debug(f"Collected dealer id {dealer_id} product id {product_id}: {city_count}")

        processed_dealer_ids.add(dealer_id)
        logger.debug(f"User with id {dealer_id} was successfully processed")

    if not new_plans:
        logger.error("Not found new `DealerKPIPlan` for saving")
        return

    logger.info(f"New `DealerKPIPlan` to creating: {len(new_plans)}")
    kpi_plans = DealerKPIPlan.objects.bulk_create(new_plans)

    new_products_to_buy = [
        ProductToBuy(kpi_plan=kpi_plan, product_id=product_id)
        for kpi_plan in kpi_plans
        for product_id in collected_products_to_buy.get(getattr(kpi_plan, "dealer_id")) or []
    ]
    logger.info(f"New `ProductToBuy` to creating: {len(new_products_to_buy)}")

    if new_products_to_buy:
        saved_products = ProductToBuy.objects.bulk_create(new_products_to_buy)
    else:
        saved_products = []  # this is needed to assemble the following list new_product_counts without nesting
        logger.warning("Not found new `ProductToBuy` for saving")

    new_product_counts = [
        CityProductToBuy(product_to_buy=saved_product, **purchase_data)
        for saved_product in saved_products
        for purchase_data in collected_product_counts.get(getattr(saved_product, "product_id")) or []
    ]

    if new_product_counts:
        logger.info(f"New `ProductToBuyCount` to creating: {len(new_product_counts)}")
        CityProductToBuy.objects.bulk_create(new_product_counts)
    else:
        logger.warning("Not found new `ProductToBuyCount` for saving")


@app.task
def create_dealer_kpi_plan_stats(user_id: int, target_month: int, target_year: int):
    kpi_plan = DealerKPIPlan.objects.filter(
        dealer_id=user_id,
        target_month=target_month,
        created_at__year=target_year
    ).first()
    if not kpi_plan:
        logging.warning(
            f"Not found `DealerKPIPlan` for user with id {user_id} "
            f"target month: {target_month} target year: {target_year}"
        )
        return

    logger.info(f"Start updating stats for `DealerKPIPlan` with id {kpi_plan.id}...")
    done_amount = MoneyDoc.objects.filter(
        user=kpi_plan.dealer,
        created_at__month=kpi_plan.target_month,
        created_at__year=kpi_plan.created_at.year,
        is_active=True
    ).aggregate(done_amount=Sum("amount"))["done_amount"]

    logger.debug(
        f"Try to update `DealerKPIPlanStat.done_amount` user ID: {user_id} "
        f"new value: {done_amount} target month: {target_month} target year: {target_year}"
    )
    DealerKPIPlanStat.objects.create(kpi_plan=kpi_plan, done_amount=done_amount)

    logger.info(f"Successfully created stats for `DealerKPIPlan` with ID: {kpi_plan.id}")


@app.task
def create_dealer_kpi_plan_product_stats(
        user_id: int,
        product_id: int,
        city_id: int,
        target_month: int,
        target_year: int
):
    city_product_to_buy = CityProductToBuy.objects.filter(
        product_to_buy__kpi_plan__dealer_id=user_id,
        product_to_buy__kpi_plan__target_month=target_month,
        product_to_buy__kpi_plan__created_at__year=target_year,
        product_to_buy__product_id=product_id,
        city_id=city_id
    ).first()
    if not city_product_to_buy:
        logger.warning(
            f"Not found `CityProductToBuy` for "
            f"user with id {user_id} product id {product_id} city id {city_id}"
            f"target month: {target_month} target year: {target_year}"
        )
        return

    logger.info(f"Start creating stats `CityProductToBuy` with id {city_product_to_buy.id}...")

    done_count = OrderProduct.objects.filter(
        order__author__user_id=user_id,
        order__is_active=True,
        order__stock__city_id=city_id,
        order__status__in=("wait", "sent", "paid", "success"),
        order__created_at__month=target_month,
        order__created_at__year=target_year,
        ab_product_id=product_id
    ).aggretate(done_count=Sum("count"))["done_count"]

    logger.debug(
        f"Try to update `CityProductToBuy` user ID: {user_id} "
        f"new value: {done_count} target month: {target_month} target year: {target_year}"
    )

    CityProductToBuyStat.objects.create(city_product_to_buy=city_product_to_buy, done_count=done_count)
    logger.info(f"Successfully created stats for `CityProductToBuy` with ID: {city_product_to_buy.id}")


