from order.models import ReturnOrderProduct, ReturnOrder, ReturnOrderProductFile
from product.models import AsiaProduct


def create_order_return_product(instance: ReturnOrder, comment, count: int, files, product_id: int):
    product_price = instance.order.order_products.filter(ab_product_id=product_id).first()
    product = AsiaProduct.objects.filter(id=product_id).first()
    return_product = ReturnOrderProduct.objects.create(
        return_order=instance,
        product=product,
        comment=comment,
        count=count,
        price=count * product_price.price
    )
    files_to_create = []
    for file in files:
        files_to_create.append(ReturnOrderProductFile(
            return_product=return_product,
            file=file
        ))
    ReturnOrderProductFile.objects.bulk_create(files_to_create)
    return return_product

