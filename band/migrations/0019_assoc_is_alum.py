# Generated by Django 4.2.11 on 2024-03-22 22:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('band', '0018_alter_section_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='assoc',
            name='is_alum',
            field=models.BooleanField(default=False),
        ),
    ]
