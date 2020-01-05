from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

class MOTD(models.Model):
    text = models.TextField(max_length=500, blank=True, null=True)
    updated = models.DateTimeField(auto_now= True)

# signals to make sure a set of preferences is created for every user
@receiver(post_save, sender=MOTD)
def make_users_dirty(sender, instance, created, **kwargs):
    m = apps.get_model('member', 'Member')
    m.objects.all().update(motd_dirty=True)
