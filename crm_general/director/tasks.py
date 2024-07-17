from django.utils import timezone

from absklad_commerce.celery import app
from account.models import DealerStatus
from crm_general.models import CRMTask
from product.models import ProductPrice, AsiaProduct


@app.task
def create_product_prices(price_type_id):
    products = AsiaProduct.objects.all()
    d_statuses = DealerStatus.objects.all()
    price_data = []
    for p in products:
        for s in d_statuses:
            price_data.append(
                ProductPrice(
                    product=p,
                    d_status=s,
                    price_type_id=price_type_id
                )
            )
    ProductPrice.objects.bulk_create(price_data)


@app.task()
def checking_tasks_statuses():
    CRMTask.objects.filter(
        is_active=True,
        status__in=["created", "waiting", "repeat"],
        end_date__lt=timezone.now()
    ).update(status="expired")
