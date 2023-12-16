# Generated by Django 4.1 on 2023-12-16 03:51

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('general_service', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('account', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AsiaProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=False)),
                ('is_show', models.BooleanField(default=False)),
                ('is_hit', models.BooleanField(default=False)),
                ('uid', models.CharField(default='00000000-0000-0000-0000-000000000000', max_length=40)),
                ('title', models.CharField(max_length=500)),
                ('vendor_code', models.CharField(blank=True, max_length=50, null=True)),
                ('made_in', models.CharField(max_length=50)),
                ('guarantee', models.IntegerField(default=0)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('video_link', models.TextField(blank=True, null=True)),
                ('weight', models.IntegerField(default=0)),
                ('package_count', models.IntegerField(default=0)),
                ('avg_rating', models.DecimalField(decimal_places=1, default=0, max_digits=2)),
                ('reviews_count', models.IntegerField(default=0)),
                ('diagram', models.FileField(blank=True, null=True, upload_to='product_diagrams')),
            ],
            options={
                'ordering': ('-updated_at',),
            },
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('slug', models.CharField(max_length=100, unique=True)),
                ('image', models.FileField(blank=True, null=True, upload_to='category')),
                ('uid', models.CharField(default='00000000-0000-0000-0000-000000000000', max_length=50)),
                ('is_active', models.BooleanField(default=False)),
                ('is_show', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('slug', models.CharField(max_length=200, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='FilterMaxMin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('max_price', models.PositiveIntegerField(default=0)),
                ('min_price', models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.DecimalField(decimal_places=1, default=0, max_digits=2)),
                ('is_active', models.BooleanField(default=True)),
                ('is_moderation', models.BooleanField(default=False)),
                ('text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='product.asiaproduct')),
            ],
            options={
                'ordering': ('-id',),
            },
        ),
        migrations.CreateModel(
            name='ReviewImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='product-images')),
                ('review', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='product.review')),
            ],
        ),
        migrations.CreateModel(
            name='ProductSize',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, max_length=200, null=True)),
                ('length', models.IntegerField(default=0)),
                ('width', models.IntegerField(default=0)),
                ('height', models.IntegerField(default=0)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sizes', to='product.asiaproduct')),
            ],
        ),
        migrations.CreateModel(
            name='ProductPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('old_price', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('discount', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('discount_status', models.CharField(choices=[('Per', 'Per'), ('Sum', 'Sum')], default='Per', max_length=5)),
                ('city', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prices', to='general_service.city')),
                ('d_status', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prices', to='account.dealerstatus')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prices', to='product.asiaproduct')),
            ],
        ),
        migrations.CreateModel(
            name='ProductImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.FileField(upload_to='product-images')),
                ('position', models.PositiveIntegerField()),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='product.asiaproduct')),
            ],
            options={
                'ordering': ('position',),
            },
        ),
        migrations.CreateModel(
            name='ProductCount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count_crm', models.IntegerField(default=0)),
                ('count_1c', models.IntegerField(default=0)),
                ('count_order', models.IntegerField(default=0)),
                ('arrival_time', models.DateTimeField(blank=True, null=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='counts', to='product.asiaproduct')),
                ('stock', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='counts', to='general_service.stock')),
            ],
        ),
        migrations.CreateModel(
            name='ProductCostPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cost_prices', to='product.asiaproduct')),
            ],
        ),
        migrations.AddIndex(
            model_name='collection',
            index=models.Index(fields=['slug'], name='product_col_slug_0d9cde_idx'),
        ),
        migrations.AddIndex(
            model_name='category',
            index=models.Index(fields=['slug'], name='product_cat_slug_93e2a7_idx'),
        ),
        migrations.AddField(
            model_name='asiaproduct',
            name='category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='products', to='product.category'),
        ),
        migrations.AddField(
            model_name='asiaproduct',
            name='collection',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='products', to='product.collection'),
        ),
    ]
