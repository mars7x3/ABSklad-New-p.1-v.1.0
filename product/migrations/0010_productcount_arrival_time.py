# Generated by Django 4.1 on 2023-11-25 17:03

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("product", "0009_rename_link_asiaproduct_video_link_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="productcount",
            name="arrival_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
