from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.db.models import Sum, F, IntegerField, Case, When, FloatField, Value, Subquery, OuterRef
from django.db.models.functions import TruncMonth
from django.utils import timezone

from account.models import MyUser
from crm_kpi.models import DealerKPI, ManagerKPISVD, ManagerKPI, DealerKPIProduct
from order.models import MyOrder, OrderProduct


def get_tmz_of_user_for_kpi(check_months, user_id):
    start_date = timezone.now() - relativedelta(months=check_months)

    user_order_products = MyOrder.objects.filter(
        author__user__id=user_id,
        created_at__gte=start_date,
        status__in=['paid', 'sent', 'success', 'wait']
    ).values(
        'author__user',
        'order_products__ab_product__id',
    ).annotate(
        total_count=Sum('order_products__count'),
        total_price=Sum('order_products__total_price'),
    )

    return user_order_products


def kpi_svd_1lvl(date: datetime):
    after_query = OrderProduct.objects.filter(
        order__is_active=True,
        order__released_at__month=date.month,
        order__released_at__year=date.year,
        order__status__in=('success', 'sent')
    )
    after_products = after_query.values_list("ab_product_id", "count")
    after_product_ids = list(map(lambda x: x[0], after_products))
    after_amount = after_query.aggregate(count_sum=Sum("count"))["count_sum"]

    before_query = ManagerKPISVD.objects.filter(
        manager_kpi__month__month=date.month,
        manager_kpi__month__year=date.year
    )
    before_products = before_query.values_list("product_id", "count")
    before_product_ids = list(map(lambda x: x[0], before_products))
    before_amount = before_query.aggregate(count_sum=Sum("count"))["count_sum"]

    old = {
        product_id: count / before_amount * 100
        for product_id, count in before_products
        if product_id not in after_product_ids
    }
    new = {
        product_id: count / after_amount * 100
        for product_id, count in after_products
        if product_id not in before_product_ids
    }
    return {
        'before_count': len(before_product_ids),
        'after_count': len(after_product_ids),
        'old_count': len(old),
        'new_count': len(new),
        'share_old': round(sum(old.values())),
        'share_new': round(sum(new.values()))
    }


def kpi_acb_1lvl(date: datetime) -> dict[str, int]:
    manager_kpi_query = ManagerKPI.objects.filter(month__month=date.month, month__year=date.year)

    total = (
        manager_kpi_query
        .aggregate(
            total=Sum("akb", output_field=IntegerField(), default=Value(0))
        )["total"]
    )
    fact = (
        MyOrder.objects.filter(
            is_active=True,
            author__managers__in=Subquery(manager_kpi_query.values("manager_id")),
            created_at__month=date.month,
            created_at__year=date.year,
            status__in=['paid', 'sent', 'success', 'wait']
        ).order_by("author__user_id").distinct("author__user_id").count()
    )
    return {
        "fact": fact,
        "total": total,
        "done_per": round(fact / total * 100) if fact > 0 and total > 0 else 0
    }


def kpi_total_info(date: datetime):
    kpis = (
        DealerKPI.objects.filter(month__month=date.month, month__year=date.year)
        .values(date=TruncMonth("month"))
        .annotate(
            fact_total_pds=Sum("fact_pds", default=0),
            fact_total_tmz_count=Sum('kpi_products__fact_count', default=0),
            fact_total_tmz_sum=Sum('kpi_products__fact_sum', default=0),
            fact_avg_price=Sum(
                Case(
                    When(
                        kpi_products__fact_sum__gt=0, kpi_products__fact_count__gt=0,
                        then=F('kpi_products__fact_sum') / F('kpi_products__fact_count')
                    ),
                    output_field=FloatField(),
                    default=Value(0.0)
                )

            ),
            total_pds=Sum("pds", default=0),
            total_tmz_count=Sum('kpi_products__count', default=0),
            total_tmz_sum=Sum('kpi_products__sum', default=0),
            avg_price=Sum(
                Case(
                    When(
                        kpi_products__sum__gt=0, kpi_products__count__gt=0,
                        then=F('kpi_products__sum') / F('kpi_products__count')
                    ),
                    output_field=FloatField(),
                    default=Value(0.0)
                )
            ),
        )
        .annotate(
            per_done_pds=Case(
                When(
                    total_pds__gt=0, fact_total_pds__gt=0,
                    then=F("total_pds") / F("fact_total_pds") * 100
                ),
                default=Value(0),
                output_field=IntegerField()
            ),
            per_done_tmz_count=Case(
                When(
                    total_tmz_count__gt=0, fact_total_tmz_count__gt=0,
                    then=F("total_tmz_count") / F("fact_total_tmz_count") * 100
                ),
                default=Value(0),
                output_field=IntegerField()
            ),
            per_done_tmz_sum=Case(
                When(
                    total_tmz_sum__gt=0, fact_total_tmz_sum__gt=0,
                    then=F("total_tmz_sum") / F("fact_total_tmz_sum") * 100
                ),
                default=Value(0),
                output_field=IntegerField()
            ),
            per_done_avg_price=Case(
                When(
                    avg_price__gt=0, fact_avg_price__gt=0,
                    then=F("avg_price") / F("fact_avg_price") * 100
                ),
                default=Value(0),
                output_field=IntegerField()
            )
        )
    )

    if kpis:
        return kpis[0]
    else:
        return {
            'fact_total_pds': 0,
            'fact_total_tmz_count': 0,
            'fact_total_tmz_sum': 0,
            'fact_avg_price': 0,

            'total_pds': 0,
            'total_tmz_count': 0,
            'total_tmz_sum': 0,
            'avg_price': 0,

            'per_done_pds': 0,
            'per_done_tmz_count': 0,
            'per_done_tmz_sum': 0,
            'per_done_avg_price': 0
        }


def kpi_main_2lvl(stat_type: str, date: datetime):
    match stat_type:
        case 'pds':
            return kpi_pds_2lvl(date)
        case 'tmz':
            return kpi_tmz_2lvl(date)
        case 'sch':
            return kpi_sch_2lvl(date)
        case 'akb':
            return kpi_akb_2lvl(date)
        case 'svd':
            return kpi_svd_2lvl(date)


def kpi_pds_2lvl(date: datetime):
    managers = MyUser.objects.filter(is_active=True, status='manager', manager_profile__is_main=True)

    managers_data = []
    for manager in managers:
        kpis = DealerKPI.objects.filter(
            month__month=date.month, month__year=date.year, user__dealer_profile__managers=manager
        ).annotate(
            fact_total_pds=Sum("fact_pds", default=0),
            total_pds=Sum("pds", default=0),
        ).values_list('fact_total_pds', 'total_pds')

        total_kpis = tuple(sum(x) for x in zip(*kpis))
        if total_kpis:
            managers_data.append({
                'name': manager.name,
                'id': manager.id,
                'fact_total_pds': round(total_kpis[0]),
                'total_pds': round(total_kpis[1]),
                'per_done_pds': round(total_kpis[1] / total_kpis[0] * 100),
            })
    return managers_data


def kpi_tmz_2lvl(date: datetime):
    managers = MyUser.objects.filter(is_active=True, status='manager', manager_profile__is_main=True)

    managers_data = []
    for manager in managers:
        kpis = DealerKPI.objects.filter(
            month__month=date.month, month__year=date.year, user__dealer_profile__managers=manager
        ).annotate(
            fact_total_tmz_count=Sum('kpi_products__fact_count', default=0),
            fact_total_tmz_sum=Sum('kpi_products__fact_sum', default=0),
            total_tmz_count=Sum('kpi_products__count', default=0),
            total_tmz_sum=Sum('kpi_products__sum', default=0),
        ).values_list('fact_total_tmz_count', 'fact_total_tmz_sum', 'total_tmz_count', 'total_tmz_sum')

        total_kpis = tuple(sum(x) for x in zip(*kpis))
        if total_kpis:
            managers_data.append({
                'name': manager.name,
                'id': manager.id,
                'fact_total_tmz_count': round(total_kpis[0]),
                'fact_total_tmz_sum': round(total_kpis[1]),
                'total_tmz_count': round(total_kpis[2]),
                'total_tmz_sum': round(total_kpis[3]),
                'per_done_tmz_count': round(total_kpis[2] / total_kpis[0] * 100),
                'per_done_tmz_sum': round(total_kpis[3] / total_kpis[1] * 100),
            })
    return managers_data


def kpi_sch_2lvl(date: datetime):
    managers = MyUser.objects.filter(is_active=True, status='manager', manager_profile__is_main=True)

    managers_data = []
    for manager in managers:
        kpis = DealerKPI.objects.filter(
            month__month=date.month, user__dealer_profile__managers=manager
        ).annotate(
            fact_avg_price=Sum(F('kpi_products__fact_sum') / F('kpi_products__fact_count'), output_field=FloatField(),
                               default=0),
            avg_price=Sum(F('kpi_products__sum') / F('kpi_products__count'), output_field=FloatField(), default=0),
        ).values_list('fact_avg_price', 'avg_price')

        total_kpis = tuple(sum(x) for x in zip(*kpis))
        if total_kpis:
            managers_data.append({
                'name': manager.name,
                'id': manager.id,
                'fact_avg_price': round(total_kpis[0]),
                'avg_price': round(total_kpis[1]),
                'per_done_avg_price': round(total_kpis[1] / total_kpis[0] * 100),
            })
    return managers_data


def kpi_akb_2lvl(date: datetime):
    managers = MyUser.objects.filter(is_active=True, status='manager', manager_profile__is_main=True)

    managers_data = []
    for manager in managers:
        plan = manager.mngr_kpis.filter(month__month=date.month, month__year=date.year).first()

        users = MyUser.objects.filter(
            is_active=True, status='dealer', dealer_profile__managers=manager,
            dealer_profile__orders__created_at__month=date.month,
            dealer_profile__orders__created_at__year=date.year,
            dealer_profile__orders__is_active=True,
            dealer_profile__orders__status__in=['sent', 'success']
        )
        managers_data.append({
            'name': manager.name,
            'id': manager.id,
            'akb': plan.akb,
            'fact_akb': users.count(),
        })
    return managers_data


def kpi_svd_2lvl(date: datetime):
    managers = MyUser.objects.filter(is_active=True, status='manager', manager_profile__is_main=True)

    managers_data = []
    for manager in managers:
        before_data = ManagerKPISVD.objects.filter(
            manager_kpi__manager=manager,
            manager_kpi__month__month=date.month,
            manager_kpi__month__year=date.year
        ).order_by("product_id").distinct("product_id").values_list("product_id", "count")
        before_count = len(before_data)

        after_user_ids = manager.dealer_profiles.all().values_list('id', flat=True)
        after_data = OrderProduct.objects.filter(
            order__author_id__in=after_user_ids,
            order__is_active=True,
            order__released_at__month=date.month,
            order__released_at__year=date.year,
            order__status__in=['success', 'sent']
        ).values_list('ab_product_id', 'count')
        after_count = len(after_data)

        old_count = 0
        share_old = 0
        sum_old = sum([count for _, count in before_data])
        after_ids = [product_id for product_id, _ in after_data]

        for product_id, count in before_data:
            if product_id not in after_ids:
                old_count += 1
                share_old += count / sum_old * 100

        new_count = 0
        share_new = 0
        sum_new = sum([count for _, count in after_data])
        before_ids = [product_id for product_id, _ in before_data]

        for product_id, count in after_data:
            if product_id not in before_ids:
                new_count += 1
                share_new += count / sum_new * 100

        managers_data.append({
            'id': manager.id,
            'name': manager.name,
            'before_count': before_count,
            'after_count': after_count,
            'old_count': old_count,
            'new_count': new_count,
            'share_old': share_old,
            'share_new': share_new
        })

    return managers_data


def kpi_pds_3lvl(manager_id: int, date: datetime) -> list[dict]:
    query = (
        DealerKPI.objects
        .filter(month__month=date.month, month__year=date.year, user__dealer_profile__managers__id=manager_id)
        .values("user_id")
        .annotate(
            name=F("user__name"),
            fact_total_pds=Sum("fact_pds", default=Value(0), output_field=IntegerField()),
            total_pds=Sum("pds", default=Value(0), output_field=IntegerField()),
        )
        .annotate(
            per_done_pds=Case(
                When(
                    total_pds__gt=0, fact_total_pds__gt=0,
                    then=F("total_pds") / F("fact_total_pds") * Value(100),
                ),
                default=Value(0),
                output_field=IntegerField()
            )
        )
    )
    collected = []
    for item in query:
        item["id"] = item.pop("user_id")
        collected.append(item)
    return collected


def kpi_tmz_3lvl(manager_id: int, date: datetime) -> list[dict]:
    query = (
        DealerKPI.objects
        .filter(month__month=date.month, month__year=date.year, user__dealer_profile__managers=manager_id)
        .values("user_id")
        .annotate(
            name=F("user__name"),
            fact_total_tmz_count=Sum('kpi_products__fact_count', default=Value(0), output_field=IntegerField()),
            fact_total_tmz_sum=Sum('kpi_products__fact_sum', default=Value(0), output_field=IntegerField()),
            total_tmz_count=Sum('kpi_products__count', default=Value(0), output_field=IntegerField()),
            total_tmz_sum=Sum('kpi_products__sum', default=Value(0), output_field=IntegerField()),
        )
        .annotate(
            per_done_tmz_count=Case(
                When(
                    total_tmz_count__gt=0, fact_total_tmz_count__gt=0,
                    then=F("total_tmz_count") / F("fact_total_tmz_count") * 100
                ),
                default=Value(0),
                output_field=IntegerField()
            ),
            per_done_tmz_sum=Case(
                When(
                    total_tmz_sum__gt=0, fact_total_tmz_sum__gt=0,
                    then=F("total_tmz_sum") / F("fact_total_tmz_sum") * 100
                ),
                default=Value(0),
                output_field=IntegerField()
            )
        )
    )
    collected = []
    for item in query:
        item["id"] = item.pop("user_id")
        collected.append(item)
    return collected


def kpi_sch_3lvl(manager_id: int, date: datetime) -> list[dict]:
    query = (
        DealerKPI.objects
        .filter(month__month=date.month, month__year=date.year, user__dealer_profile__managers=manager_id)
        .values("user_id")
        .annotate(
            name=F("user__name"),
            fact_avg_price=Sum(
                F('kpi_products__fact_sum') / F('kpi_products__fact_count'),
                output_field=FloatField(),
                default=Value(0.0)
            ),
            avg_price=Sum(
                F('kpi_products__sum') / F('kpi_products__count'),
                output_field=FloatField(),
                default=Value(0.0)
            )
        )
        .annotate(
            per_done_avg_price=Case(
                When(
                    fact_avg_price__gt=0, avg_price__gt=0,
                    then=F("avg_price") / F("fact_avg_price") * 100
                ),
                default=Value(0),
                output_field=IntegerField()
            )
        )
    )
    collected = []
    for item in query:
        item["id"] = item.pop("user_id")
        item["avg_price"] = round(item["avg_price"])
        item["fact_avg_price"] = round(item["fact_avg_price"])
        collected.append(item)
    return collected


def kpi_akb_3lvl(manager_id: int, date: datetime) -> list[dict]:
    return MyUser.objects.filter(
        dealer_profile__managers=manager_id,
        is_active=True,
        status='dealer',
        dealer_profile__orders__created_at__month=date.month,
        dealer_profile__orders__created_at__year=date.year,
        dealer_profile__orders__is_active=True,
        dealer_profile__orders__status__in=['sent', 'success']
    ).values("id", "name").order_by("id").distinct("id")


def kpi_svd_3lvl(manager_id: int, date: datetime):
    order_products_query = OrderProduct.objects.filter(
        order__author__managers=manager_id,
        order__is_active=True,
        order__released_at__month=date.month,
        order__released_at__year=date.year,
        order__status__in=('success', 'sent')
    )
    items = (
        ManagerKPISVD.objects.filter(
            manager_kpi__manager_id=manager_id,
            manager_kpi__month__month=date.month,
            manager_kpi__month__year=date.year
        )
        .values("product_id")
        .annotate(
            title=F("product__title"),
            plan=Sum("count"),
            total_fact=Subquery(
                order_products_query.filter(ab_product_id=OuterRef("product_id"))
                .values("ab_product_id")
                .annotate(
                    total_count=Sum("count", default=Value(0), output_field=IntegerField())
                ).values("total_count")[:1],
                default=Value(0)
            )
        )
        .annotate(
            fact=Case(
                When(total_fact__isnull=True, then=Value(0)),
                default=F("total_fact")
            )
        )
        .annotate(
            done_per=Case(
                When(
                    fact__gt=0, plan__gt=0,
                    then=F("fact") / F("plan") * 100
                ),
                default=Value(0),
                output_field=IntegerField()
            )
        )
    )

    data = []
    for item in items:
        item.pop("total_fact", None)
        item["id"] = item.pop("product_id")
        data.append(item)
    return data


def kpi_main_3lvl(stat_type: str, manager_id: int, date: datetime):
    match stat_type:
        case 'pds':
            return kpi_pds_3lvl(manager_id, date)
        case 'tmz':
            return kpi_tmz_3lvl(manager_id, date)
        case 'sch':
            return kpi_sch_3lvl(manager_id, date)
        case 'akb':
            return kpi_akb_3lvl(manager_id, date)
        case 'svd':
            return kpi_svd_3lvl(manager_id, date)


def update_dealer_kpi_product(order_product: OrderProduct) -> bool:
    order = order_product.order
    dealer_kpi = DealerKPIProduct.objects.filter(
        product_id=order.product.id,
        kpi__user_id=getattr(order.author, "user_id"),
        kpi__month__month=order.released_at.month,
        kpi__month__year=order.released_at.year
    ).first()

    if not dealer_kpi:
        return False

    if order.is_active:
        dealer_kpi.fact_count += order.product.count
        dealer_kpi.fact_sum += order.product.total_price
    else:
        dealer_kpi.fact_count -= order.product.count
        dealer_kpi.fact_sum -= order.product.total_price
    dealer_kpi.save()
    return True


def update_dealer_kpi(order: MyOrder):
    dealer_kpi = DealerKPI.objects.filter(
        month__month=order.released_at.month,
        month__year=order.released_at.year,
        user=order.author.user
    ).first()

    if not dealer_kpi:
        return

    saved_product_ids = dealer_kpi.kpi_products.values_list("product_id", flat=True)
    new_products_kpi = []

    for order_product in order.order_products.all():
        if order_product.ab_product.id not in saved_product_ids:
            new_products_kpi.append(
                DealerKPIProduct(
                    kpi=dealer_kpi,
                    product=order_product.ab_product,
                    fact_count=order_product.count,
                    fact_sum=order_product.total_price
                )
            )
        else:
            update_dealer_kpi_product(order_product)

    if new_products_kpi:
        DealerKPIProduct.objects.bulk_create(new_products_kpi)