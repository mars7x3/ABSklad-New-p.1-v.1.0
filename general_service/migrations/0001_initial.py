# Generated by Django 4.1 on 2023-12-16 04:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CashBox',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=30)),
                ('uid', models.CharField(blank=True, max_length=40, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=20)),
                ('slug', models.SlugField(max_length=30, unique=True)),
                ('user_uid', models.CharField(blank=True, max_length=40, null=True)),
                ('price_uid', models.CharField(blank=True, max_length=40, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('is_show', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Stock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.TextField(blank=True, null=True)),
                ('schedule', models.TextField(blank=True, null=True)),
                ('uid', models.CharField(blank=True, max_length=40, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('is_show', models.BooleanField(default=True)),
                ('city', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='stocks', to='general_service.city')),
            ],
        ),
        migrations.CreateModel(
            name='StockPhone',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(max_length=30)),
                ('stock', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='phones', to='general_service.stock')),
            ],
        ),
        migrations.AddIndex(
            model_name='city',
            index=models.Index(fields=['slug'], name='general_ser_slug_adb2e9_idx'),
        ),
        migrations.AddField(
            model_name='cashbox',
            name='stock',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cash_box', to='general_service.stock'),
        ),
    ]
