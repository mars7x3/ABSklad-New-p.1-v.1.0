from order.models import MyOrder


def check_reservation(order_id):
    order = MyOrder.objects.filter(id=order_id).select_related('author__user')
    user = order.author.user
    reservations = user.reservations.filter(is_active=True)
    for p in order.order_products.all():
        reservation = reservations.filter(product=p, stock=order.stock).first()
        if reservation:
            reservation.count -= p.count
            if reservation.count <= 0:
                reservation.is_success = True
                reservation.is_active = False
            reservation.save()
