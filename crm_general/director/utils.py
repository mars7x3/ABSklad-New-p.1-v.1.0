from django.db.models import Sum, Case, When, Value, IntegerField, F

from order.models import MyOrder


def get_motivation_done(dealer):
    motivations_data = []
    motivations = dealer.motivations.filter(is_active=True)

    for motivation in motivations:
        motivation_data = {
            "title": motivation.title,
            "start_date": motivation.start_date,
            "end_date": motivation.end_date,
            "is_active": motivation.is_active,
            "conditions": []
        }

        conditions = motivation.conditions.all()
        orders = dealer.orders.filter(
            is_active=True, status__in=['sent', 'sent', 'success', 'wait'],
            paid_at__gte=motivation.start_date)

        for condition in conditions:
            condition_data = {
                "status": condition.status,
                "presents": []
            }

            if condition.status == 'category':
                condition_data["condition_cats"] = []
                condition_cats = condition.condition_cats.all()
                for condition_cat in condition_cats:
                    category_data = {
                        "count": condition_cat.count,
                        "category": condition_cat.category.id,
                        "category_title": condition_cat.category.title
                    }
                    condition_data["condition_cats"].append(category_data)
                    total_count = sum(
                        order_products.count
                        for order in orders
                        for order_products in order.order_products.filter(category=condition_cat.category)
                    )
                    condition_data['done'] = total_count
                    condition_data['per'] = round(total_count * 100 / condition_cat.count)

            elif condition.status == 'product':
                condition_data["condition_prods"] = []
                condition_prods = condition.condition_prods.all()
                for condition_prod in condition_prods:
                    product_data = {
                        "count": condition_prod.count,
                        "product": condition_prod.product.id,
                        "product_title": condition_prod.product.title
                    }
                    condition_data["condition_prods"].append(product_data)

                    total_count = sum(
                        order_products.count
                        for order in orders
                        for order_products in order.order_products.filter(ab_product=condition_prod.product)
                    )
                    condition_data['done'] = total_count
                    condition_data['per'] = round(total_count * 100 / condition_prod.count)

            elif condition.status == 'money':
                condition_data["money"] = condition.money
                total_count = sum(orders.values_list('price', flat=True))
                condition_data['done'] = total_count
                condition_data['per'] = round(total_count * 100 / condition.money)

            presents = condition.presents.all()
            for p in presents:
                present_data = {
                    "status": p.status,
                    "money": p.money,
                    "text": p.text
                }

                condition_data["presents"].append(present_data)

            motivation_data["conditions"].append(condition_data)

        motivations_data.append(motivation_data)

    return motivations_data


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
    pass






