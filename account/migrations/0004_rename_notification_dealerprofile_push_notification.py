# Generated by Django 4.1 on 2023-11-25 13:36

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("account", "0003_dealerprofile_notification"),
    ]

    operations = [
        migrations.RenameField(
            model_name="dealerprofile",
            old_name="notification",
            new_name="push_notification",
        ),
    ]
