# Generated by Django 4.1 on 2024-01-15 15:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm_stat', '0008_remove_purchasestat_cost_price_stockgroupstat'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockgroupstat',
            name='incoming_users_count',
            field=models.IntegerField(default=0),
        ),
    ]
