# Generated by Django 4.1 on 2023-12-16 04:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('general_service', '0001_initial'),
        ('product', '0001_initial'),
        ('account', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dealer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='carts', to='account.dealerprofile')),
                ('stock', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='cart', to='general_service.stock')),
            ],
        ),
        migrations.CreateModel(
            name='MyOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=100, null=True)),
                ('gmail', models.CharField(blank=True, max_length=100, null=True)),
                ('phone', models.CharField(blank=True, max_length=100, null=True)),
                ('address', models.CharField(blank=True, max_length=300, null=True)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('cost_price', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('status', models.CharField(choices=[('Новый', 'Новый'), ('Оплачено', 'Оплачено'), ('Отправлено', 'Отправлено'), ('Ожидание', 'Ожидание'), ('Отказано', 'Отказано'), ('Успешно', 'Успешно')], default='Новый', max_length=15)),
                ('type_status', models.CharField(blank=True, choices=[('Наличка', 'Наличка'), ('Карта', 'Карта'), ('Баллы', 'Баллы'), ('Каспи', 'Каспи')], max_length=15, null=True)),
                ('comment', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('released_at', models.DateTimeField(blank=True, null=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('uid', models.CharField(default='00000000-0000-0000-0000-000000000000', max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('author', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='account.dealerprofile')),
                ('stock', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='general_service.stock')),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='ReturnOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('Новый', 'Новый'), ('Успешно', 'Успешно'), ('Отказано', 'Отказано')], default='Новый', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('moder_comment', models.TextField(blank=True, null=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='returns', to='order.myorder')),
            ],
            options={
                'ordering': ('-id',),
            },
        ),
        migrations.CreateModel(
            name='ReturnOrderProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count', models.IntegerField(default=0)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='return_products', to='product.asiaproduct')),
                ('returns_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='return_products', to='order.returnorder')),
            ],
        ),
        migrations.CreateModel(
            name='OrderReceipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='order-check')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_receipts', to='order.myorder')),
            ],
        ),
        migrations.CreateModel(
            name='OrderProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=500)),
                ('count', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('total_price', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('discount', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('image', models.FileField(blank=True, null=True, upload_to='order-product')),
                ('ab_product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_products', to='product.asiaproduct')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_products', to='product.category')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_products', to='order.myorder')),
            ],
        ),
        migrations.CreateModel(
            name='OrderMoney',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('uid', models.CharField(default='00000000-0000-0000-0000-000000000000', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('cash_box', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_moneys', to='general_service.cashbox')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_moneys', to='order.myorder')),
            ],
        ),
        migrations.CreateModel(
            name='CartProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count', models.IntegerField(default=0)),
                ('cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cart_products', to='order.cart')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cart_products', to='product.asiaproduct')),
            ],
        ),
    ]
