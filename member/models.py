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
from motd.models import MOTD
from gig.models import Plan, GigStatusChoices
from gig.util import PlanStatusChoices
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
import datetime
from django.utils import timezone
from .util import MemberStatusChoices, AgendaChoices, AgendaLayoutChoices
from band.models import Assoc, Band
from band.util import AssocStatusChoices
from go3.settings import LANGUAGES
from lib.email import EmailRecipient
from lib.caldav import delete_calfeed
import uuid

class MemberManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email, and password.
        """
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email).lower()
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

    def active(self):
        return self.all().filter(status=MemberStatusChoices.ACTIVE)


# a 1-1 link to user model
# https://simpleisbetterthancomplex.com/tutorial/2016/07/22/how-to-extend-django-user-model.html#onetoone


class Member(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)

    username = models.CharField(max_length=200)
    nickname = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=100, blank=True, null=True)
    statement = models.CharField(max_length=500, blank=True, null=True)
    motd_dirty = models.BooleanField(default=True)
    seen_welcome = models.BooleanField(default=False)
    # pending_change_email = ndb.TextProperty(default='', indexed=False)
    images = models.TextField(max_length=500, blank=True, null=True)

    # flag to determine whether to recompute calendar feed
    cal_feed_dirty = models.BooleanField(default=True)
    cal_feed_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    status = models.IntegerField(choices=MemberStatusChoices.choices, default=MemberStatusChoices.ACTIVE)

    # The old Gig-O-Matic v2 (Google App Engine) member ID
    # Used to map old calendar subscription URLs
    go2_id = models.CharField(max_length=100, blank=True)

    display_name = models.CharField(max_length=200, blank=True, null=True)

    # used for testing new features on a few people
    is_beta_tester = models.BooleanField(default=False)

    @property
    def member_name(self):
        return self.username if self.username else self.email

    @property
    def band_count(self):
        """ return number of bands for which I'm confirmed """
        return Assoc.member_assocs.confirmed_count(self)

    @property
    def confirmed_assocs(self):
        """ return gigs for bands the member is confirmed """
        return Assoc.member_assocs.confirmed_assocs(self)

    @property
    def add_gig_assocs(self):
        """ return the assocs for bands the member can create gigs for """
        return Assoc.member_assocs.add_gig_assocs(self)

    @property
    def future_plans(self):
        """ used by the agenda page to decide what gigs to show """
        plans = Plan.member_plans.future_plans(self)
        
        if self.preferences.hide_canceled_gigs: # pylint: disable=no-member
            # hide all canceled gigs and gigs without plans
            plans = plans.exclude(gig__status=GigStatusChoices.CANCELED).exclude(status=PlanStatusChoices.NO_PLAN)
        else:
            # filter out gigs without plans unless they are canceled
            plans = plans.exclude(Q(status=PlanStatusChoices.NO_PLAN)&~Q(gig__status=GigStatusChoices.CANCELED))

        plans = plans.exclude(assoc__hide_from_schedule=True)
        return plans

    @property
    def future_noplans(self):
        """ used by the agenda page to decide what gigs to show """
        plans = Plan.member_plans.future_plans(self).filter(status=PlanStatusChoices.NO_PLAN)
        plans = plans.exclude(gig__status=GigStatusChoices.CANCELED)        
        plans = plans.exclude(assoc__hide_from_schedule=True)
        plans = plans.exclude(Q(assoc__is_occasional=True) & Q(gig__invite_occasionals=False))
        return plans
    
    @property
    def calendar_plans(self):
        """ pick the gigs that should go on the calendar """
        """ returns plans, not gigs, in case they need to be further filtered """

        # first get all of the plans which meet the criteria
        filter_args = {
            "assoc__member": self, # my plan
            "assoc__status": AssocStatusChoices.CONFIRMED, # is a usual member
            "assoc__hide_from_schedule": False, # gigs are not hidden from calendar
            "gig__hide_from_calendar": False, # not hidden from calendars
            "gig__trashed_date__isnull": True, # not trashed
        }

        if self.preferences.calendar_show_only_confirmed:  # pylint: disable=no-member
            filter_args["gig__status"] = GigStatusChoices.CONFIRMED

        if self.preferences.calendar_show_only_committed:  # pylint: disable=no-member
            filter_args["status__in"] = [
                PlanStatusChoices.DEFINITELY, PlanStatusChoices.PROBABLY]

        # get the plans but exclude gigs for which occasionals are not invited if we're occasional in the band
        plans = Plan.objects.filter(**filter_args)


        plans = plans.exclude(Q(assoc__is_occasional=True) & Q(gig__invite_occasionals=False) & Q(status=PlanStatusChoices.NO_PLAN))
        if self.preferences.hide_canceled_gigs: # pylint: disable=no-member
            plans = plans.exclude(gig__status=GigStatusChoices.CANCELED)

        return plans

    @property
    def motd(self):
        if self.motd_dirty:
            the_motd = MOTD.objects.first()
        else:
            the_motd = None
        return the_motd.text if the_motd else None

    def as_email_recipient(self):
        return EmailRecipient(name=self.username, email=self.email,
                              language=self.preferences.language) # pylint: disable=no-member

    def save(self, *args, **kwargs):
        """ when creating members with a form, the usermanager isn't used so we have to override save """
        self.email = self.email.lower()
        # then super
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """ when we get deleted, remove plans for future gigs and set us to deleted """
        Plan.member_plans.future_plans(self).filter(gig__is_archived=False).delete()
        delete_calfeed(self.cal_feed_id)
        self.status = MemberStatusChoices.DELETED
        self.is_active = False
        self.email = "user_{0}@gig-o-matic.com".format(self.id)
        self.username = "deleted user"
        self.nickname = ''
        self.phone = ''
        self.statement = ''
        self.set_unusable_password()
        self.save()

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
        return '{0} ({1}) {2}'.format(self.display_name, self.email, ' (deleted)' if self.status==MemberStatusChoices.DELETED else '')


class MemberPreferences(models.Model):
    """ class to hold user preferences """
    member = models.OneToOneField(Member, related_name='preferences', on_delete=models.CASCADE)

    hide_canceled_gigs = models.BooleanField(default=False, verbose_name=_('Hide canceled gigs'))
    language = models.CharField(choices=LANGUAGES, max_length=200, default='en-US', verbose_name=_('Language'))
    share_profile = models.BooleanField(default=True, verbose_name=_('Share my profile'))
    share_email = models.BooleanField(default=False, verbose_name=_('Share my email'))
    calendar_show_only_confirmed = models.BooleanField(default=False, verbose_name=_('Calendar shows only confirmed gigs'))
    calendar_show_only_committed = models.BooleanField(default=False, verbose_name=_('Calendar shows only gigs I can do (or maybe can do)'))
    agenda_show_time = models.BooleanField(default=True, verbose_name=_('Show gig time on schedule'))
    agenda_layout = models.IntegerField(choices=AgendaLayoutChoices.choices, 
                                        default=AgendaLayoutChoices.ONE_LIST,
                                        verbose_name=_('Schedule page layout'))
    agenda_band = models.ForeignKey(Band, null=True, on_delete=models.SET_NULL)
    agenda_use_classic = models.BooleanField(default=False, verbose_name=_('Use old schedule page layout'))


    default_view = models.IntegerField(choices=AgendaChoices.choices, default=AgendaChoices.AGENDA)


class Invite(models.Model):
    """
    An invitation sent to an email address.  The recipient can sign up with that or
    another email address.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    band = models.ForeignKey(Band, related_name="invites", on_delete=models.CASCADE, null=True)
    email = models.EmailField(_('email address'))
    language = models.CharField(choices=LANGUAGES, max_length=200, default='en-US')

    def as_email_recipient(self):
        return EmailRecipient(email=self.email, language=self.language)


class EmailConfirmation(models.Model):
    """
    When a user wants to change email addresses, send an email to them with a link
    they can use to confirm that they really own it.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(Member, related_name="pending_email", on_delete=models.CASCADE, null=True)
    new_email = models.EmailField(_('new email'))
    language = models.CharField(choices=LANGUAGES, max_length=200, default='en-US')

    def as_email_recipient(self):
        return EmailRecipient(email=self.new_email, language=self.language)
