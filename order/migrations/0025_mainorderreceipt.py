# Generated by Django 4.2 on 2024-03-04 16:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0024_alter_mainorderproduct_order'),
    ]

    operations = [
        migrations.CreateModel(
            name='MainOrderReceipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='main-order-check')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='receipts', to='order.mainorder')),
            ],
        ),
    ]
