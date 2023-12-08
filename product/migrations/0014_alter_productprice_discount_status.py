# Generated by Django 4.1 on 2023-12-07 15:48

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("product", "0013_alter_productprice_discount_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="productprice",
            name="discount_status",
            field=models.CharField(
                choices=[("Per", "Per"), ("Sum", "Sum")], default="Per", max_length=5
            ),
        ),
    ]
