from django.utils import timezone

from order.models import ReturnOrderProduct, ReturnOrder, ReturnOrderProductFile, MainOrderProduct
from product.models import AsiaProduct


def create_order_return_product(instance: ReturnOrder, comment, count: int, files, product_id: int):
    product = AsiaProduct.objects.filter(id=product_id).first()
    return_product = ReturnOrderProduct.objects.create(
        return_order=instance,
        product=product,
        comment=comment,
        count=count,
    )
    files_to_create = []
    for file in files:
        files_to_create.append(ReturnOrderProductFile(
            return_product=return_product,
            file=file
        ))
    ReturnOrderProductFile.objects.bulk_create(files_to_create)
    return return_product


def create_validated_data(main_order):
    validated_data = {
        'main_order': main_order,
        'author': main_order.author,
        # 'creator': main_order.creator,
        'stock': main_order.stock,
        'status': 'sent',
        'type_status': main_order.type_status,
        'created_at': main_order.created_at,
        'released_at': timezone.localtime().now(),
        'paid_at': main_order.paid_at,
        # 'price': main_order.price,
        # 'cost_price': main_order.author,
    }
    return validated_data


def minus_count(main_order, products):
    update_data = []
    for p in products:
        d_prod = main_order.products.filter(ab_product=p['ab_product']).first()
        if d_prod:
            d_prod.count -= p['count']
            update_data.append(d_prod)

    MainOrderProduct.objects.bulk_update(update_data, ['count'])
