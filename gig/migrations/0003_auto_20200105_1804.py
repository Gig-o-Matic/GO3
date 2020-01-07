# Generated by Django 3.0 on 2020-01-05 23:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gig', '0002_auto_20200105_1800'),
    ]

    operations = [
        migrations.AddField(
            model_name='gig',
            name='creator',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_gigs', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='gig',
            name='default_to_attending',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='gig',
            name='hide_from_calendar',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='gig',
            name='invite_occasionals',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='gig',
            name='is_private',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='gig',
            name='trashed_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='gig',
            name='was_reminded',
            field=models.BooleanField(default=False),
        ),
    ]