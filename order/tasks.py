from account.models import Notification
from order.models import MyOrder
from absklad_commerce.celery import app


@app.task()
def create_order_notification(order_id):
    order = MyOrder.objects.get(id=order_id)
    kwargs = {'user': order.author.user, 'status': 'order', 'title': f'Заказ #{order.id}',
              'description': order.comment, 'link_id': order.id, 'is_push': True}

    notification = Notification.objects.create(**kwargs)
    return notification




