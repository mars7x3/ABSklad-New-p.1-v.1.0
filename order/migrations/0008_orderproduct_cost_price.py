# Generated by Django 4.2 on 2023-12-24 11:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0007_alter_myorder_status_alter_returnorder_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderproduct',
            name='cost_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=100),
        ),
    ]
