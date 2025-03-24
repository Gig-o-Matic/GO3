# Generated by Django 4.2.15 on 2025-03-08 19:39

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gig', '0028_restore_gig_timezone_dates'),
    ]

    operations = [
        migrations.AddField(
            model_name='gig',
            name='watchers',
            field=models.ManyToManyField(related_name='watching', to=settings.AUTH_USER_MODEL),
        ),
    ]
