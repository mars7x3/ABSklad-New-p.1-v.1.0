# Generated by Django 4.2 on 2024-02-01 11:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0031_crmnotification_is_pushed_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='crmnotification',
            name='dealer_profiles',
            field=models.ManyToManyField(blank=True, related_name='crm_notifications', to='account.dealerprofile'),
        ),
    ]
