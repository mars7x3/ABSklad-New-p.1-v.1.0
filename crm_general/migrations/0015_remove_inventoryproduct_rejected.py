# Generated by Django 4.2 on 2024-01-30 20:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crm_general', '0014_merge_20240129_1548'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='inventoryproduct',
            name='rejected',
        ),
    ]
