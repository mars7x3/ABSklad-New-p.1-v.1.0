# Generated by Django 4.1 on 2023-12-21 10:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0003_balancehistory_balance'),
        ('promotion', '0007_banner'),
    ]

    operations = [
        migrations.AddField(
            model_name='banner',
            name='groups',
            field=models.ManyToManyField(related_name='banner_groups', to='account.dealerstatus'),
        ),
    ]
