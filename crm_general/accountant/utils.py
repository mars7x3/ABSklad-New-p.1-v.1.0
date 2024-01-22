from order.models import MyOrder, OrderProduct
from product.models import ProductCount


def deduct_returned_product_from_order_and_stock(order: MyOrder, product_id: int, count: int):
    order_product = OrderProduct.objects.get(order_id=order, ab_product_id=product_id)
    product_count = order_product.count
    product_price = order_product.price
    deducted = product_count - count
    if deducted <= 0:
        order_product.delete()
    else:
        order_product.count -= count
        order_product.price = (order_product.count - count) * product_price
        order_product.save()

    stock = ProductCount.objects.filter(stock_id=order.stock.id).first()
    stock.count_crm += count
    stock.save()


