from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

class Band(models.Model):
    name = models.CharField(max_length=200)
    hometown = models.CharField(max_length=200, null=True)

    shortname = models.CharField(max_length=200, null=True)
    condensed_name = models.CharField(max_length=200, null=True)

    # website = ndb.TextProperty()
    # description = ndb.TextProperty()
    # sections = ndb.KeyProperty(repeated=True)  # instrumental sections
    # created = ndb.DateTimeProperty(auto_now_add=True)
    # timezone = ndb.StringProperty(default='UTC')
    # thumbnail_img = ndb.TextProperty(default=None)
    # images = ndb.TextProperty(repeated=True)
    # member_links = ndb.TextProperty(default=None)

    # # sent to new members when they join
    # new_member_message = ndb.TextProperty(default=None)

    # share_gigs = models.BooleanField(default=True)
    # anyone_can_manage_gigs = models.BooleanField(default=True)
    # anyone_can_create_gigs = models.BooleanField(default=True)
    # send_updates_by_default = models.BooleanField(default=True)
    # rss_feed = models.BooleanField(default=False)
    
    # simple_planning = models.BooleanField(default=False)
    # plan_feedback = ndb.TextProperty()

    # # determines whether this band shows up in the band navigator - useful for hiding test bands
    # show_in_nav = models.BooleanField(default=True)
    
    # # flags to determine whether to recompute calendar feeds
    # band_cal_feed_dirty = models.BooleanField(default=True)
    # pub_cal_feed_dirty = ndb.BooleanProperty(default=True)

    def __str__(self):
        return self.name

@receiver(pre_save, sender=Band)
def my_handler(sender, instance, **kwargs):
    instance.condensed_name = ''.join(instance.name.split()).lower()

class Assoc(models.Model):
    band = models.ForeignKey(Band, related_name="assocs", on_delete=models.CASCADE)
    member = models.ForeignKey("member.Member", verbose_name="member", related_name="assocs", on_delete=models.CASCADE)

    def __str__(self):
        return "{0} in {1}".format(self.member, self.band)

