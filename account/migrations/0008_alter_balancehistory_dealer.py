# Generated by Django 4.2 on 2023-12-22 11:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0007_merge_20231222_1057'),
    ]

    operations = [
        migrations.AlterField(
            model_name='balancehistory',
            name='dealer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='balance_histories', to='account.dealerprofile'),
        ),
    ]
