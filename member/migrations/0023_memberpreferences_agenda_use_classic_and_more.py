# Generated by Django 4.2.11 on 2024-07-20 22:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('member', '0022_alter_memberpreferences_agenda_layout'),
    ]

    operations = [
        migrations.AddField(
            model_name='memberpreferences',
            name='agenda_use_classic',
            field=models.BooleanField(default=False, verbose_name='Use classic schedule page'),
        ),
        migrations.AlterField(
            model_name='memberpreferences',
            name='agenda_layout',
            field=models.IntegerField(choices=[(0, 'Weigh In'), (1, 'By Band'), (2, 'Single List'), (3, 'Has Response')], default=2, verbose_name='Schedule page layout'),
        ),
    ]
