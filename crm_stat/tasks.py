from datetime import datetime

from django.db.models.functions import TruncDate
from django.utils import timezone

from absklad_commerce.celery import app
from order.models import MyOrder

from .collectors import collects_stats_for_date, save_stock_group_for_day, save_stock_group_for_month
from .models import PurchaseStat


@app.task
def collect_today_stats():
    today = timezone.now()
    collects_stats_for_date(today)


@app.task
def collect_for_all_dates():
    dates = set(order["date"] for order in MyOrder.objects.filter(is_active=True).values(date=TruncDate("created_at")))
    for date in dates:
        collects_stats_for_date(datetime(month=date.month, year=date.year, day=date.day))


@app.task
def collect_today_stock_groups():
    today = timezone.now().date()
    save_stock_group_for_day(today)
    # save_stock_group_for_week(today)
    save_stock_group_for_month(today)


@app.task
def collect_stock_groups_for_all():
    dates = set(PurchaseStat.objects.values_list("date", flat=True))
    processed_months = set()

    for date in dates:
        if (date.month, date.year) not in processed_months:
            save_stock_group_for_month(date)
            processed_months.add((date.month, date.year))

        save_stock_group_for_day(date)
