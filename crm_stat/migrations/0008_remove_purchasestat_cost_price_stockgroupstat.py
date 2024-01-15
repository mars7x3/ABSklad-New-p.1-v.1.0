# Generated by Django 4.1 on 2024-01-15 06:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crm_stat', '0007_remove_citystat_date_remove_productstat_date_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='purchasestat',
            name='cost_price',
        ),
        migrations.CreateModel(
            name='StockGroupStat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('stat_type', models.CharField(choices=[('month', 'Month'), ('week', 'Week'), ('day', 'Day')], max_length=10)),
                ('incoming_bank_amount', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
                ('incoming_cash_amount', models.DecimalField(decimal_places=2, default=0, max_digits=20)),
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
                ('stock_stat', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_stats', to='crm_stat.stockstat')),
            ],
            options={
                'unique_together': {('stat_type', 'stock_stat', 'date')},
            },
        ),
    ]
