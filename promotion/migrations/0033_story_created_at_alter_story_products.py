# Generated by Django 4.2 on 2024-01-27 11:55

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0013_alter_asiaproduct_made_in'),
        ('promotion', '0032_discountprice_price_type_alter_discountprice_city'),
    ]

    operations = [
        migrations.AddField(
            model_name='story',
            name='created_at',
            field=models.DateField(auto_now_add=True, default=datetime.datetime(2024, 1, 27, 11, 55, 24, 893893, tzinfo=datetime.timezone.utc)),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='story',
            name='products',
            field=models.ManyToManyField(blank=True, related_name='stories', to='product.asiaproduct'),
        ),
    ]
