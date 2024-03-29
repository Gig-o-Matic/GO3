# Generated by Django 4.2.10 on 2024-03-13 23:30

from django.db import migrations


def add_display_name(apps, schema_editor):
    Member = apps.get_model('member','Member')
    for m in Member.objects.all():
        if not m.display_name:
            if m.nickname:
                m.display_name = m.nickname
            elif m.username:
                m.display_name = m.username
            else:
                m.display_name = m.email
            m.save()

def remove_display_name(apps, schema_editor):
    return

class Migration(migrations.Migration):

    dependencies = [
        ('member', '0014_member_display_name'),
    ]

    operations = [
        migrations.RunPython(add_display_name, remove_display_name)
    ]
