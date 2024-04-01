from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Subquery, OuterRef, F

from order.models import MainOrder, MainOrderProduct
from product.models import AsiaProduct, ProductPrice, ProductImage, ProductCostPrice


def order_total_price(product_counts, dealer_status, city=None, price_type=None):
    assert city or price_type
    filters = dict(product_id__in=list(product_counts), d_status_id=dealer_status)
    if price_type:
        filters['price_type_id'] = price_type
    else:
        filters['city_id'] = city
    prices = (
        ProductPrice.objects.only("product_id", "price")
        .filter(**filters)
    )
    return sum([price_obj.price * product_counts[str(price_obj.product_id)] for price_obj in prices])


def check_to_unavailable_products(product_counts: dict[str: int], stock) -> list[dict[str, int]]:
    stock_product_counts = (
        stock.counts.filter(product_id__in=list(product_counts))
        .values("product_id", "count_crm")
        .order_by("product_id").distinct("product_id")
    )
    return [
        count_data
        for count_data in stock_product_counts
        if product_counts[str(count_data['product_id'])] > count_data['count_crm']
    ]


def calculate_order_cost_price(product_counts: dict[str: int]):
    product_cost_prices = (
        ProductCostPrice.objects.filter(is_active=True, product_id__in=list(product_counts))
        .values_list("product_id", "price")
        .order_by("product_id").distinct("product_id")

    )
    return sum([price * product_counts[str(p_id)] for p_id, price in product_cost_prices])


def build_order_products_data(product_counts: dict[str: int], dealer_status, city=None, price_type=None):
    assert city or price_type
    product_ids = list(product_counts)
    db_product_data = (
        AsiaProduct.objects.filter(id__in=product_ids)
        .values("category_id", "title", ab_product_id=F("id"))
        .annotate(
            image=Subquery(
                ProductImage.objects.filter(product_id=OuterRef("id"))
                .values("image")[:1]
            )
        )
    )
    filters = dict(product_id__in=product_ids, d_status=dealer_status)
    if price_type:
        filters['price_type'] = price_type
    else:
        filters['city'] = city

    prices = (
        ProductPrice.objects.filter(**filters)
        .values_list("product_id", "price", "old_price")
        .order_by("product_id").distinct("product_id")
    )
    collected_prices = {product_id: (price, old_price) for product_id, price, old_price in prices}
    if not collected_prices:
        raise ObjectDoesNotExist("ProductPrice with filters %s does not exists" % filters)

    collected_products = []
    for product_data in db_product_data:
        product_id = product_data['ab_product_id']
        price, old_price = collected_prices[product_id]
        count = product_counts[str(product_id)]
        collected_products.append(
            {
                # **product_data,
                'ab_product': AsiaProduct.objects.get(id=product_data['ab_product_id']),
                "price": price,
                # "total_price": price * count,
                # "discount": abs(old_price - price) if old_price > 0 else 0,
                "count": count
            }
        )
    return collected_products


def update_main_order_product_count(main_order: MainOrder, product_counts: dict[str:int]):
    main_order_products = MainOrderProduct.objects.filter(order=main_order, ab_product_id__in=list(product_counts))
    data_to_update = []
    total_price = 0
    for main_order_product in main_order_products:
        count = product_counts[str(main_order_product.ab_product.id)]
        if count > 0:
            main_order_product.count = count
            total_price += main_order_product.price * count
            data_to_update.append(main_order_product)
        else:
            main_order_product.delete()
    MainOrderProduct.objects.bulk_update(data_to_update, ['count'])
    main_order.price = total_price
    main_order.save()
    return main_order


