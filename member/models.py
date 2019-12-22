from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from band.models import Band, Assoc

# a 1-1 link to user model
# https://simpleisbetterthancomplex.com/tutorial/2016/07/22/how-to-extend-django-user-model.html#onetoone
class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    nickname = models.CharField(max_length=100, default=None )
    phone = models.CharField(max_length=100, default='')
    statement = models.TextField(default='')

    # is_band_editor = ndb.BooleanProperty(default=False)
    # created = ndb.DateTimeProperty(auto_now_add=True)
    # preferences = ndb.StructuredProperty(MemberPreferences)
    # seen_motd = ndb.BooleanProperty(default=False) # deprecated
    # seen_motd_time = ndb.DateTimeProperty(default=None)
    # seen_welcome = ndb.BooleanProperty(default=False)
    # show_long_agenda = ndb.BooleanProperty(default=True)
    # pending_change_email = ndb.TextProperty(default='', indexed=False)
    # images = ndb.TextProperty(repeated=True)
    # display_name = ndb.ComputedProperty(lambda self: self.nickname if self.nickname else self.name)
    # last_activity = ndb.DateTimeProperty(auto_now=True)
    # last_calfetch = ndb.DateTimeProperty(default=None)
    # local_email_address = ndb.ComputedProperty(lambda self: self.email_address)
    # cal_feed_dirty = ndb.BooleanProperty(default=True)

    class Meta:
        permissions = (
            ("beta_tester", "Is A Beta Tester"),
        )

    def __str__(self):
        return self.name

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Member.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.member.save()

