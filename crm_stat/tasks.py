from datetime import datetime

from absklad_commerce.celery import app
from account.utils import sync_balance_history
from crm_kpi.utils import update_dealer_kpi_by_tx, update_dealer_kpi_by_order

from .models import UserTransactionsStat, PurchaseStat, StockGroupStat
from .utils import create_empty_group_stat, update_purchase_stat_group, update_tx_stat_group, \
    update_stat_group_by_order, update_transaction_stat


@app.task()
def task_update_tx_stat_group(tx_stat_id):
    tx_stat = UserTransactionsStat.objects.get(id=tx_stat_id)

    day_group_stat = StockGroupStat.objects.filter(
        date=tx_stat.date,
        stat_type=StockGroupStat.StatType.day,
        stock=tx_stat.stock
    ).first()

    if not day_group_stat:
        day_group_stat = create_empty_group_stat(
            date=tx_stat.date,
            stat_type=StockGroupStat.StatType.day,
            stock=tx_stat.stock
        )

    update_tx_stat_group(
        group=day_group_stat,
        queryset=UserTransactionsStat.objects.filter(date=tx_stat.date, stock=tx_stat.stock)
    )

    month_group_stat = StockGroupStat.objects.filter(
        date__month=tx_stat.date.month,
        date__year=tx_stat.date.year,
        stat_type=StockGroupStat.StatType.month,
        stock=tx_stat.stock
    ).first()
    if not month_group_stat:
        month_group_stat = create_empty_group_stat(
            date=datetime(year=tx_stat.date.year, month=tx_stat.date.month, day=1),
            stat_type=StockGroupStat.StatType.month,
            stock=tx_stat.stock
        )

    update_tx_stat_group(
        group=month_group_stat,
        queryset=UserTransactionsStat.objects.filter(
            date__month=tx_stat.date.month,
            date__year=tx_stat.date.year,
            stock=tx_stat.stock
        )
    )


@app.task()
def task_update_purchase_stat_group(purchase_stat_id):
    purchase_stat = PurchaseStat.objects.get(id=purchase_stat_id)
    day_group_stat = StockGroupStat.objects.filter(
        date=purchase_stat.date,
        stat_type=StockGroupStat.StatType.day,
        stock=purchase_stat.stock
    ).first()

    if not day_group_stat:
        day_group_stat = create_empty_group_stat(
            date=purchase_stat.date,
            stat_type=StockGroupStat.StatType.day,
            stock=purchase_stat.stock
        )

    update_purchase_stat_group(
        group=day_group_stat,
        queryset=PurchaseStat.objects.filter(date=purchase_stat.date, stock=purchase_stat.stock)
    )

    month_group_stat = StockGroupStat.objects.filter(
        date__month=purchase_stat.date.month,
        date__year=purchase_stat.date.year,
        stat_type=StockGroupStat.StatType.month,
        stock=purchase_stat.stock
    ).first()
    if not month_group_stat:
        month_group_stat = create_empty_group_stat(
            date=datetime(year=purchase_stat.date.year, month=purchase_stat.date.month, day=1),
            stat_type=StockGroupStat.StatType.month,
            stock=purchase_stat.stock
        )

    update_purchase_stat_group(
        group=month_group_stat,
        queryset=PurchaseStat.objects.filter(
            date__month=purchase_stat.date.month,
            date__year=purchase_stat.date.year,
            stock=purchase_stat.stock
        )
    )


@app.task()
def main_stat_order_sync(order):
    update_stat_group_by_order(order)
    update_dealer_kpi_by_order(order)
    sync_balance_history(order, 'order')


@app.task()
def main_stat_pds_sync(money_doc):
    update_dealer_kpi_by_tx(money_doc)
    update_transaction_stat(money_doc)
    sync_balance_history(money_doc, 'wallet')
