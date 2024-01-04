from decimal import Decimal

from django.db.models import Sum, Case, When, Value, F, Subquery, OuterRef, DecimalField, FloatField, Q
from django.db.models.functions import Coalesce, Round
from django.utils import timezone

from order.models import MyOrder


def get_motivation_margin(motivation):
    amount = 0
    for condition in motivation.conditions.all():
        match condition.status:
            case 'category':
                total_amount = 0
                for cat in condition.condition_cats.all():
                    total_amount += sum(cat.category.order_products.filter(
                        order__is_active=True, order__status__in=['paid', 'sent', 'wait', 'success'],
                        order__paid_at__gte=motivation.start_date, order__paid_at__lte=motivation.end_date,
                        order__author__in=motivation.dealers.all()
                    ).values_list('total_price', flat=True))
                amount += total_amount

            case 'product':
                total_amount = 0
                for prod in condition.condition_prods.all():
                    total_amount += sum(prod.product.order_products.filter(
                        order__is_active=True, order__status__in=['paid', 'sent', 'wait', 'success'],
                        order__paid_at__gte=motivation.start_date, order__paid_at__lte=motivation.end_date,
                        order__author__in=motivation.dealers.all()
                    ).values_list('total_price', flat=True))
                amount += total_amount

            case 'money':
                total_amount = sum(MyOrder.objects.filter(
                    is_active=True, status__in=['paid', 'sent', 'wait', 'success'],
                    paid_at__gte=motivation.start_date, paid_at__lte=motivation.end_date,
                    author__in=motivation.dealers.all()
                ).values_list('price', flat=True))
                amount += total_amount

    return amount


def kpi_info(kpi):
    executor_cities = ()
    match kpi.executor.status:
        case "rop":
            executor_cities = kpi.executor.rop_profile.citites.values_list("id", flat=True)
        case "manager":
            executor_cities = (kpi.executor.manager_profile.city.id,)

    match kpi.status:
        case 3:
            order_subquery = Subquery(
                MyOrder.objects.filter(
                    paid_at__date__gte=OuterRef("start_date"),
                    paid_at__date__lte=OuterRef("end_date"),
                    status__in=("paid", "sent", "wait", "success"),
                    author__city_id__in=executor_cities
                ).annotate(amount=Sum("price")).values("amount")
            )
        case 1:
            order_subquery = Subquery(
                MyOrder.objects.filter(
                    paid_at__date__gte=OuterRef("start_date"),
                    paid_at__date__lte=OuterRef("end_date"),
                    status__in=("paid", "sent", "wait", "success"),
                    author__city_id__in=executor_cities,
                    order_products__ab_product_id__in=OuterRef("products"),
                ).annotate(amount=Sum("order_products__count")).values("amount")
            )
        case _:
            order_subquery = Subquery(
                MyOrder.objects.filter(
                    paid_at__date__gte=OuterRef("start_date"),
                    paid_at__date__lte=OuterRef("end_date"),
                    status__in=("paid", "sent", "wait", "success"),
                    author__city_id__in=executor_cities,
                    order_products__ab_product__category_id__in=OuterRef("categories"),
                ).annotate(amount=Sum("order_products__count")).values("amount")
            )

    now = timezone.now()
    return (
        kpi.kpi_items.filter(start_date__lte=now, end_date__gte=now)
        .annotate(
            status_f=F("kpi__status"),
            plan=Sum("amount", output_field=DecimalField()),
            fact=Coalesce(order_subquery, Value(Decimal("0"))),
        )
        .annotate(
            uspevaemost=F("fact") - F("plan"),
            index=Round(
                Case(
                    When(fact__gt=0, plan__gt=0, then=F("fact") / (F("plan") / Value(100.0))),
                    default=Value(0.0),
                    output_field=FloatField()
                ),
                precision=2
            )
        )
        .values("plan", "fact", "uspevaemost", "index")
    )
