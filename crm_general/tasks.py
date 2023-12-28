from absklad_commerce.celery import app
from general_service.models import Stock
from order.models import MyOrder
from product.models import ProductCount


@app.task
def minus_quantity(order_id, stock_id):
    order = MyOrder.objects.get(id=order_id)
    stock = Stock.objects.get(id=stock_id)
    products_id = order.order_products.all().values_list('ab_product_id', 'count')
    counts = ProductCount.objects.filter(stock=stock)
    for p_id, count in products_id:
        quantity = counts.get(product_id=p_id)
        quantity.count -= count
        quantity.save()
