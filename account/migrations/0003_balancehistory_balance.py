# Generated by Django 4.1 on 2023-12-17 21:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0002_alter_wallet_options_balancehistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='balancehistory',
            name='balance',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=100),
        ),
    ]
