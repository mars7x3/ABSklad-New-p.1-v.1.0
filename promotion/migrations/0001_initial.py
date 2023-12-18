# Generated by Django 4.1 on 2023-12-16 04:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('product', '0001_initial'),
        ('account', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Target',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('completed', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('dealer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='targets', to='account.dealerprofile')),
            ],
        ),
        migrations.CreateModel(
            name='TargetPresent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('product', 'Товар'), ('money', 'Деньги'), ('text', 'Прочее')], default='money', max_length=10)),
                ('text', models.TextField(blank=True, null=True)),
                ('money', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='present_products', to='product.asiaproduct')),
                ('target', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='presents', to='promotion.target')),
            ],
        ),
        migrations.CreateModel(
            name='Story',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=False)),
                ('title', models.CharField(max_length=300)),
                ('slogan', models.CharField(max_length=300)),
                ('text', models.TextField()),
                ('image', models.FileField(blank=True, null=True, upload_to='stories_files')),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
                ('products', models.ManyToManyField(related_name='stories', to='product.asiaproduct')),
            ],
        ),
    ]
