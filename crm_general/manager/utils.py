from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Subquery, OuterRef, F

from product.models import AsiaProduct, ProductPrice, ProductImage, ProductCostPrice


def order_total_price(product_counts, price_type, dealer_status):
    prices = (
        ProductPrice.objects.only("product_id", "price")
                            .filter(product_id__in=list(product_counts),
                                    price_type=price_type,
                                    d_status_id=dealer_status)
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


def build_order_products_data(product_counts: dict[str: int], price_type, dealer_status):
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
    filters = dict(product_id__in=product_ids, price_type=price_type, d_status=dealer_status)
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
                **product_data,
                "price": price,
                "total_price": price * count,
                "discount": abs(old_price - price) if old_price > 0 else 0,
                "count": count
            }
        )
    return collected_products
