# Generated by Django 4.2.15 on 2024-11-08 16:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('member', '0026_memberpreferences_current_timezone'),
    ]

    operations = [
        migrations.AddField(
            model_name='memberpreferences',
            name='auto_update_timezone',
            field=models.BooleanField(default=True, verbose_name='Automatically Update Timezone'),
        ),
    ]