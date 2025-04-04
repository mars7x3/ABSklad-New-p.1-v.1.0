# Generated by Django 4.2 on 2024-06-28 09:51

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('general_service', '0001_initial'),
        ('product', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserTransactionsStat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('bank_income', models.DecimalField(decimal_places=2, max_digits=20)),
                ('cash_income', models.DecimalField(decimal_places=2, max_digits=20)),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='general_service.stock')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PurchaseStat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('spent_amount', models.DecimalField(decimal_places=2, max_digits=20)),
                ('count', models.PositiveIntegerField()),
                ('purchases_count', models.PositiveIntegerField(default=0)),
                ('avg_check', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='purchases', to='product.asiaproduct')),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='purchases', to='general_service.stock')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='purchases', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StockGroupStat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('stat_type', models.CharField(choices=[('month', 'Month'), ('day', 'Day')], max_length=10)),
                ('incoming_bank_amount', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('incoming_cash_amount', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('incoming_users_count', models.IntegerField(default=0)),
                ('sales_products_count', models.IntegerField(default=0)),
                ('sales_amount', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('sales_count', models.IntegerField(default=0)),
                ('sales_users_count', models.IntegerField(default=0)),
                ('sales_avg_check', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('dealers_incoming_funds', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('dealers_products_count', models.IntegerField(default=0)),
                ('dealers_amount', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('dealers_avg_check', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('products_amount', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('products_user_count', models.IntegerField(default=0)),
                ('products_avg_check', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_stats', to='general_service.stock')),
            ],
            options={
                'unique_together': {('stat_type', 'stock', 'date')},
            },
        ),
    ]
