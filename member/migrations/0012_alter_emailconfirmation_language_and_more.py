# Generated by Django 4.2.10 on 2024-03-09 17:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('member', '0011_auto_20210904_0952'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailconfirmation',
            name='language',
            field=models.CharField(choices=[('de', 'German'), ('en-US', 'English (US)'), ('en-GB', 'English (UK, AU, NZ, ...)'), ('fr', 'French'), ('it', 'Italian')], default='en-US', max_length=200),
        ),
        migrations.AlterField(
            model_name='invite',
            name='language',
            field=models.CharField(choices=[('de', 'German'), ('en-US', 'English (US)'), ('en-GB', 'English (UK, AU, NZ, ...)'), ('fr', 'French'), ('it', 'Italian')], default='en-US', max_length=200),
        ),
        migrations.AlterField(
            model_name='memberpreferences',
            name='language',
            field=models.CharField(choices=[('de', 'German'), ('en-US', 'English (US)'), ('en-GB', 'English (UK, AU, NZ, ...)'), ('fr', 'French'), ('it', 'Italian')], default='en-US', max_length=200),
        ),
    ]
