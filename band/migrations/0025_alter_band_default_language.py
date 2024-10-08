# Generated by Django 4.2.14 on 2024-09-27 18:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('band', '0024_alter_band_default_language'),
    ]

    operations = [
        migrations.AlterField(
            model_name='band',
            name='default_language',
            field=models.CharField(choices=[('de', 'Deutsch'), ('en-US', 'English (US)'), ('en-GB', 'English (UK, AU, NZ, ...)'), ('es', 'Español'), ('fr', 'Français'), ('it', 'Italiano')], default='en-US', max_length=200),
        ),
    ]
