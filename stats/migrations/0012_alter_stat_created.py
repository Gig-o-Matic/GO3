# Generated by Django 4.2.11 on 2024-06-01 15:49

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0011_alter_metric_kind_alter_stat_created'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stat',
            name='created',
            field=models.DateField(default=django.utils.timezone.now),
        ),
    ]