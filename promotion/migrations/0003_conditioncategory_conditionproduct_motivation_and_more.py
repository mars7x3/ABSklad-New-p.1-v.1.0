# Generated by Django 4.2 on 2023-12-19 02:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0003_balancehistory_balance'),
        ('product', '0004_alter_productimage_options_and_more'),
        ('promotion', '0002_discount_discountproduct_discountdealerstatus_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConditionCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count', models.IntegerField(default=0)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='condition_cats', to='product.category')),
            ],
        ),
        migrations.CreateModel(
            name='ConditionProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Motivation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=300)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('dealers', models.ManyToManyField(related_name='motivations', to='account.dealerprofile')),
            ],
        ),
        migrations.CreateModel(
            name='MotivationCondition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('category', 'category'), ('money', 'money'), ('product', 'product')], max_length=10)),
                ('money', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('text', models.TextField(blank=True, null=True)),
                ('motivation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conditions', to='promotion.motivation')),
            ],
        ),
        migrations.CreateModel(
            name='MotivationPresent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('product', 'Товар'), ('money', 'Деньги'), ('text', 'Прочее')], default='money', max_length=10)),
                ('money', models.DecimalField(decimal_places=2, default=0, max_digits=100)),
                ('text', models.TextField(blank=True, null=True)),
                ('motivation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='presents', to='promotion.motivation')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='present_products', to='product.asiaproduct')),
            ],
        ),
        migrations.RemoveField(
            model_name='targetpresent',
            name='product',
        ),
        migrations.RemoveField(
            model_name='targetpresent',
            name='target',
        ),
        migrations.DeleteModel(
            name='Target',
        ),
        migrations.DeleteModel(
            name='TargetPresent',
        ),
        migrations.AddField(
            model_name='conditionproduct',
            name='condition',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='condition_prods', to='promotion.motivation'),
        ),
        migrations.AddField(
            model_name='conditionproduct',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='condition_prods', to='product.asiaproduct'),
        ),
        migrations.AddField(
            model_name='conditioncategory',
            name='condition',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='condition_cats', to='promotion.motivation'),
        ),
    ]
