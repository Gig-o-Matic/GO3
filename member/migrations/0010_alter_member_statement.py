# Generated by Django 3.2.3 on 2021-05-30 20:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('member', '0009_auto_20210425_1732'),
    ]

    operations = [
        migrations.AlterField(
            model_name='member',
            name='statement',
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
