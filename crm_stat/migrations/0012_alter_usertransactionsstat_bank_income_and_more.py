# Generated by Django 4.2 on 2024-01-23 12:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm_stat', '0011_alter_stockstat_city_stat_alter_userstat_city_stat'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usertransactionsstat',
            name='bank_income',
            field=models.DecimalField(decimal_places=2, max_digits=20),
        ),
        migrations.AlterField(
            model_name='usertransactionsstat',
            name='cash_income',
            field=models.DecimalField(decimal_places=2, max_digits=20),
        ),
    ]
