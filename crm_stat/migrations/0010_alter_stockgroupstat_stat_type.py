# Generated by Django 4.2 on 2024-01-16 12:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm_stat', '0009_stockgroupstat_incoming_users_count'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stockgroupstat',
            name='stat_type',
            field=models.CharField(choices=[('month', 'Month'), ('day', 'Day')], max_length=10),
        ),
    ]
