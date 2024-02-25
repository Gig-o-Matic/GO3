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

from django.db import models
from django.db.models import Q
from go3.colors import the_colors
from .util import BandStatusChoices, AssocStatusChoices
from member.util import MemberStatusChoices, AgendaChoices
from django.apps import apps
import pytz
import uuid
from go3.settings import LANGUAGES


class Band(models.Model):
    name = models.CharField(max_length=200)
    hometown = models.CharField(max_length=200, null=True, blank=True)

    shortname = models.CharField(max_length=200, null=True, blank=True)
    condensed_name = models.CharField(max_length=200, null=True, blank=True)

    website = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(max_length=500, null=True, blank=True)
    images = models.TextField(max_length=500, null=True, blank=True)
    member_links = models.TextField(max_length=500, null=True, blank=True)
    thumbnail_img = models.CharField(max_length=500, null=True, blank=True)

    timezone = models.CharField(
        max_length=200, default="UTC", choices=[(x, x) for x in pytz.common_timezones]
    )

    # # sent to new members when they join
    new_member_message = models.TextField(max_length=500, null=True, blank=True)

    share_gigs = models.BooleanField(default=True)
    anyone_can_manage_gigs = models.BooleanField(default=True)
    anyone_can_create_gigs = models.BooleanField(default=True)
    send_updates_by_default = models.BooleanField(default=True)
    rss_feed = models.BooleanField(default=False)

    simple_planning = models.BooleanField(default=False)
    plan_feedback = models.TextField(max_length=500, blank=True, null=True)

    @property
    def feedback_strings(self):
        return self.plan_feedback.split("\n")

    status = models.IntegerField(
        choices=BandStatusChoices.choices, default=BandStatusChoices.ACTIVE
    )

    creation_date = models.DateField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    # # determines whether this band shows up in the band navigator - useful for hiding test bands
    # show_in_nav = models.BooleanField(default=True)

    # # flags to determine whether to recompute calendar feeds
    # band_cal_feed_dirty = models.BooleanField(default=True)
    pub_cal_feed_dirty = models.BooleanField(default=True)
    pub_cal_feed_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    default_language = models.CharField(
        choices=LANGUAGES, max_length=200, default="en-us"
    )

    def has_member(self, member):
        return (
            member
            and not member.is_anonymous
            and self.assocs.filter(
                member=member, status=AssocStatusChoices.CONFIRMED
            ).count()
            == 1
        )

    def is_admin(self, member):
        not_anon = not member.is_anonymous
        is_confirmed = (
            self.assocs.filter(
                member=member, status=AssocStatusChoices.CONFIRMED, is_admin=True
            ).count()
            == 1
        )
        is_super = member.is_superuser
        return member and (is_super or (not_anon and is_confirmed))

    def is_editor(self, member):
        return (
            member
            and not member.is_anonymous
            and (self.is_admin(member) or member.is_superuser)
        )

    @property
    def all_assocs(self):
        return self.assocs.filter(member__status=MemberStatusChoices.ACTIVE)

    @property
    def confirmed_assocs(self):
        return self.assocs.filter(
            status=AssocStatusChoices.CONFIRMED,
            member__status=MemberStatusChoices.ACTIVE,
        )

    @property
    def confirmed_members(self):
        return apps.get_model("member", "Member").objects.filter(
            assocs__status=AssocStatusChoices.CONFIRMED,
            assocs__band=self,
            status=MemberStatusChoices.ACTIVE,
        )

    @property
    def band_admins(self):
        return self.confirmed_assocs.filter(is_admin=True)

    @property
    def trash_gigs(self):
        return self.gigs.filter(trashed_date__isnull=False)

    @property
    def archive_gigs(self):
        return self.gigs.filter(is_archived=True)

    def __str__(self):
        return self.name


class SectionManager(models.Manager):
    def populated(self):
        # find out if there are any members in the default section
        s = self.all().filter(is_default=True).first()
        if Assoc.objects.filter(default_section=s).count():
            return self.all()
        else:
            return self.all().filter(is_default=False)


class Section(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    order = models.IntegerField(default=0)
    band = models.ForeignKey(Band, related_name="sections", on_delete=models.CASCADE)

    is_default = models.BooleanField(default=False)

    objects = SectionManager()

    def __str__(self):
        return "{0} in {1}".format(
            self.name if self.name else "No Section", self.band.name
        )

    class Meta:
        ordering = ["order"]


class MemberAssocManager(models.Manager):
    """functions on the Assoc class that are queries for members"""

    def confirmed_count(self, member):
        """returns the asocs for bands we're confirmed for"""
        return (
            super()
            .get_queryset()
            .filter(member=member, status=AssocStatusChoices.CONFIRMED)
            .count()
        )

    def confirmed_assocs(self, member):
        """returns the asocs for bands we're confirmed for"""
        return (
            super()
            .get_queryset()
            .filter(
                member=member,
                member__status=MemberStatusChoices.ACTIVE,
                status=AssocStatusChoices.CONFIRMED,
            )
        )

    def add_gig_assocs(self, member):
        """return the assocs for bands the member can create gigs for"""
        return (
            super()
            .get_queryset()
            .filter(
                Q(member=member)
                & Q(status=AssocStatusChoices.CONFIRMED)
                & (
                    Q(member__is_superuser=True)
                    | Q(is_admin=True)
                    | Q(band__anyone_can_create_gigs=True)
                )
            )
        )


class Assoc(models.Model):
    band = models.ForeignKey(Band, related_name="assocs", on_delete=models.CASCADE)
    member = models.ForeignKey(
        "member.Member",
        verbose_name="member",
        related_name="assocs",
        on_delete=models.CASCADE,
    )
    default_section = models.ForeignKey(
        Section,
        null=True,
        blank=True,
        related_name="default_assocs",
        on_delete=models.DO_NOTHING,
    )

    status = models.IntegerField(
        choices=AssocStatusChoices.choices, default=AssocStatusChoices.NOT_CONFIRMED
    )

    is_admin = models.BooleanField(default=False)
    is_occasional = models.BooleanField(default=False)

    join_date = models.DateField(auto_now_add=True)

    @property
    def is_confirmed(self):
        return self.status == AssocStatusChoices.CONFIRMED

    @property
    def is_pending(self):
        return self.status == AssocStatusChoices.PENDING

    @property
    def is_alum(self):
        return self.status == AssocStatusChoices.ALUMNI

    @property
    def section(self):
        if self.default_section is None:
            return self.band.sections.get(is_default=True)
        else:
            return self.default_section

    # default_section_index = ndb.IntegerProperty( default=None )

    is_multisectional = models.BooleanField(default=False)
    # commitment_number = ndb.IntegerProperty(default=0)
    # commitment_total = ndb.IntegerProperty(default=0)
    color = models.IntegerField(default=0)

    @property
    def colorval(self):
        return the_colors[self.color]

    email_me = models.BooleanField(default=True)
    hide_from_schedule = models.BooleanField(default=False)

    objects = models.Manager()
    member_assocs = MemberAssocManager()

    def __str__(self):
        return "{0} in {1} ({2})".format(self.member, self.band, self.status)
