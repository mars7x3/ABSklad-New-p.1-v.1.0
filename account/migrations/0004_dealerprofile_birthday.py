# Generated by Django 4.2 on 2023-12-19 07:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0003_balancehistory_balance'),
    ]

    operations = [
        migrations.AddField(
            model_name='dealerprofile',
            name='birthday',
            field=models.DateField(blank=True, null=True),
        ),
    ]
