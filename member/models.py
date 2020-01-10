"""
    This file is part of Gig-o-Matic

    Gig-o-Matic is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.db.models import Q
from django.dispatch import receiver
from band.models import Band, Assoc
from motd.models import MOTD
from django.utils.translation import gettext_lazy as _
import datetime
from django.utils import timezone

class MemberManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email, and password.
        """
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None,  **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None,  **extra_fields):
        """
        Creates and saves a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


# a 1-1 link to user model
# https://simpleisbetterthancomplex.com/tutorial/2016/07/22/how-to-extend-django-user-model.html#onetoone


class Member(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)

    username = models.CharField(max_length=200)
    nickname = models.CharField(max_length=100, blank=True )
    phone = models.CharField(max_length=100, blank=True)
    statement = models.CharField(max_length=200, blank=True)
    motd_dirty = models.BooleanField(default=True)
    seen_welcome = models.BooleanField(default=False)
    show_long_agenda = models.BooleanField(default=True)
    # pending_change_email = ndb.TextProperty(default='', indexed=False)
    images = models.TextField(max_length=500, blank=True)

    # flag to determine whether to recompute calendar feed
    cal_feed_dirty = models.BooleanField(default=True)

    @property
    def display_name(self):
        if self.nickname:
            return self.nickname
        elif self.username:
            return self.username
        else:
            return self.email

    @property
    def member_name(self):
        return self.username if self.username else self.email

    @property
    def confirmed_assocs(self):
        return self.assocs.filter(is_confirmed=True)

    @property
    def add_gig_assocs(self):
        if self.is_superuser:
            return self.assocs
        else:
            return self.assocs.filter( Q(is_confirmed=True) & (Q(is_band_admin=True) | Q(band__anyone_can_create_gigs=True)) )

    @property
    def motd(self):
        if self.motd_dirty:
            the_motd = MOTD.objects.first()
        else:
            the_motd = None
        return the_motd.text if the_motd else None

    objects = MemberManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        permissions = (
            ("beta_tester", "Is A Beta Tester"),
        )
        verbose_name = _('member')
        verbose_name_plural = _('members')

    def __str__(self):
        return '{0}'.format(self.display_name)


class MemberPreferences(models.Model):
    """ class to hold user preferences """
    member = models.OneToOneField(Member, related_name='preferences', on_delete=models.CASCADE)

    hide_canceled_gigs = models.BooleanField(default=False)
    locale = models.CharField(max_length=200, default='en')
    share_profile = models.BooleanField(default=True)
    share_email = models.BooleanField(default=False)
    calendar_show_only_confirmed = models.BooleanField(default=True)
    calendar_show_only_committed = models.BooleanField(default=True)
    default_view = models.IntegerField(default=0) # 0 = agenda, 1 = calendar, 2 = grid
    agenda_show_time = models.BooleanField(default=False)


# signals to make sure a set of preferences is created for every user
@receiver(post_save, sender=Member)
def create_user_preferences(sender, instance, created, **kwargs):
    if created:
        MemberPreferences.objects.create(member=instance)

@receiver(post_save, sender=Member)
def save_user_preferences(sender, instance, **kwargs):
    instance.preferences.save()

