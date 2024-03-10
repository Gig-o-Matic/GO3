# Generated by Django 4.2.10 on 2024-03-09 17:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('band', '0014_alter_band_default_language'),
        ('gig', '0012_auto_20210604_1736'),
    ]

    operations = [
        migrations.AddField(
            model_name='gig',
            name='email_changes',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='historicalgig',
            name='email_changes',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='gig',
            name='band',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)ss', related_query_name='%(class)ss', to='band.band'),
        ),
        migrations.AlterField(
            model_name='gig',
            name='status',
            field=models.IntegerField(choices=[(0, 'Unconfirmed'), (1, 'Confirmed'), (2, 'Cancelled'), (3, 'Asking')], default=0),
        ),
        migrations.AlterField(
            model_name='historicalgig',
            name='status',
            field=models.IntegerField(choices=[(0, 'Unconfirmed'), (1, 'Confirmed'), (2, 'Cancelled'), (3, 'Asking')], default=0),
        ),
    ]