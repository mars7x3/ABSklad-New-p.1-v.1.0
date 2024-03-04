# Generated by Django 4.2 on 2024-02-02 11:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0020_myorder_creator'),
    ]

    operations = [
        migrations.AddField(
            model_name='returnorder',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='returnorderproduct',
            name='comment',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='returnorderproduct',
            name='price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=100),
        ),
    ]
