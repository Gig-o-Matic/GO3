# Generated by Django 4.2.11 on 2024-07-03 20:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('band', '0024_alter_band_default_language'),
        ('member', '0020_memberpreferences_agenda_layout'),
    ]

    operations = [
        migrations.AddField(
            model_name='memberpreferences',
            name='agenda_band',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='band.band'),
        ),
    ]
