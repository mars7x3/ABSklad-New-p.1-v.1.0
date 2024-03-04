
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm_stat', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stat',
            name='amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=9),
        ),
        migrations.AlterField(
            model_name='stat',
            name='cost_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=9),
        ),
    ]
