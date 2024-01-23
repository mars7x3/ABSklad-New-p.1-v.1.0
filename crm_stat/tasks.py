from datetime import datetime

from django.db.models.functions import TruncDate
from django.utils import timezone

from absklad_commerce.celery import app
from one_c.models import MoneyDoc
from order.models import MyOrder

from .collectors import collects_stats_for_date, save_stock_group_for_day, save_stock_group_for_month, \
    collect_city_stats, collect_stock_stats, collect_user_stats, collect_product_stats
from .models import PurchaseStat, UserTransactionsStat


@app.task
def collect_stat_objects():
    collect_city_stats()
    collect_stock_stats()
    collect_user_stats()
    collect_product_stats()


@app.task
def collect_for_all_dates():
    collect_stat_objects()
    dates = set(
        order["date"]
        for order in MyOrder.objects.filter(is_active=True)
                                    .values(date=TruncDate("released_at"))
    )
    tx_dates = set(
        tx["date"]
        for tx in MoneyDoc.objects.filter(is_active=True, cash_box__isnull=False)
                                  .values(date=TruncDate("created_at"))
    )

    for date in dates | tx_dates:
        collects_stats_for_date(datetime(month=date.month, year=date.year, day=date.day))


@app.task
def collect_stock_groups_for_all():
    dates = set(PurchaseStat.objects.values_list("date", flat=True))
    dates |= set(UserTransactionsStat.objects.values_list("date", flat=True))
    processed_months = set()

    for date in dates:
        if (date.month, date.year) not in processed_months:
            save_stock_group_for_month(date)
            processed_months.add((date.month, date.year))

        save_stock_group_for_day(date)


@app.task()
def day_stat_task():
    today = timezone.now()

    collect_stat_objects()

    # collect today stats
    collects_stats_for_date(today)

    # collect stock group stats
    save_stock_group_for_day(today.date())
    save_stock_group_for_month(today.date())
