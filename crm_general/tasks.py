import logging

from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from django.utils.timezone import now

from absklad_commerce.celery import app
from crm_general.models import DealerKPIPlan, ProductToBuyCount
from crm_general.utils import create_dealer_kpi_plans
from general_service.models import Stock
from one_c.models import MoneyDoc
from order.models import MyOrder, OrderProduct
from product.models import ProductCount


@app.task
def minus_quantity(order_id, stock_id):
    order = MyOrder.objects.get(id=order_id)
    stock = Stock.objects.get(id=stock_id)
    products_id = order.order_products.all().values_list('ab_product_id', 'count')
    counts = ProductCount.objects.filter(stock=stock)
    for p_id, count in products_id:
        quantity = counts.get(product_id=p_id)
        quantity.count -= count
        quantity.save()


@app.task()
def create_dealer_kpi_to_next_month():
    create_dealer_kpi_plans(target_month=(now() + relativedelta(months=1)).month, months=3)


@app.task
def update_dealer_kpi_plan_done(user_id: int):
    kpi_plan = DealerKPIPlan.objects.filter(dealer_id=user_id, target_month=now().month).first()
    if not kpi_plan:
        logging.warning("Now found kpi plan for user with id %s" % user_id)
        return

    kpi_plan.done_amount = MoneyDoc.objects.filter(
        user=kpi_plan.dealer,
        created_at__month=kpi_plan.target_month,
        is_active=True
    ).aggregate(done_amount=Sum("amount"))["done_amount"]
    kpi_plan.save()


@app.task
def update_dealer_kpi_plan_product_done(user_id: int, product_id: int, city_id: int):
    target_month = now().month
    count_product_to_buy = ProductToBuyCount.objects.filter(
        product_to_buy__kpi_plan__dealer_id=user_id,
        product_to_buy__kpi_plan__target_month=target_month,
        product_to_buy__product_id=product_id,
        city_id=city_id
    ).first()
    if not count_product_to_buy:
        logging.warning(
            "Now found kpi plan for user with id %s product id %s city id %s" % (user_id, product_id, city_id)
        )
        return

    count_product_to_buy.done_count = OrderProduct.objects.filter(
        order__author__user_id=user_id,
        order__stock__city_id=city_id,
        order__status__in=("wait", "sent", "paid", "success"),
        order__created_at__month=target_month,
        ab_product_id=product_id
    ).aggretate(done_count=Sum("count"))["done_count"]
    count_product_to_buy.save()
