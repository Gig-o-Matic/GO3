# Generated by Django 3.1.7 on 2021-03-17 02:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("stats", "0008_auto_20210316_2154"),
    ]

    operations = [
        migrations.RenameField(
            model_name="stat",
            old_name="updated",
            new_name="created",
        ),
    ]
