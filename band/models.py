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

class Band(models.Model):
    name = models.CharField(max_length=200)
    hometown = models.CharField(max_length=200, null=True, blank=True)

    shortname = models.CharField(max_length=200, null=True, blank=True)
    condensed_name = models.CharField(max_length=200, null=True, blank=True)

    website = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(max_length=500, null=True, blank=True)
    images = models.TextField(max_length=500, null=True, blank=True)
    member_links = models.TextField(max_length=500, null=True, blank=True)
    thumbnail_img = models.CharField(max_length=200, null=True, blank=True)

    timezone = models.CharField(max_length=200, default='UTC')

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
        return self.plan_feedback.split('\n')

    status = models.IntegerField(choices=BandStatusChoices.choices, default=BandStatusChoices.ACTIVE)


    creation_date = models.DateField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    # # determines whether this band shows up in the band navigator - useful for hiding test bands
    # show_in_nav = models.BooleanField(default=True)
    
    # # flags to determine whether to recompute calendar feeds
    # band_cal_feed_dirty = models.BooleanField(default=True)
    # pub_cal_feed_dirty = ndb.BooleanProperty(default=True)

    def has_member(self, member):
        return self.assocs.filter(member=member, status=AssocStatusChoices.CONFIRMED).count()==1

    def is_admin(self, member):
        return self.assocs.filter(member=member, status=AssocStatusChoices.CONFIRMED, is_admin=True).count()==1

    @property
    def all_assocs(self):
        return self.assocs.filter(member__status=MemberStatusChoices.ACTIVE)

    @property
    def confirmed_assocs(self):
        return self.assocs.filter(status=AssocStatusChoices.CONFIRMED, member__status=MemberStatusChoices.ACTIVE)

    def __str__(self):
        return self.name


class Section(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    order = models.IntegerField(default=0)
    band = models.ForeignKey(Band, related_name="sections", on_delete=models.CASCADE)

    is_default = models.BooleanField(default=False)

    def __str__(self):
        return '{0} in {1}'.format(self.name if self.name else 'No Section', self.band.name)
        
    class Meta:
        ordering = ['order']


class MemberAssocManager(models.Manager):
    """ functions on the Assoc class that are queries for members """
    def confirmed_count(self, member):
        """ returns the asocs for bands we're confirmed for """
        return super().get_queryset().filter(member=member, status=AssocStatusChoices.CONFIRMED).count()

    def confirmed_assocs(self, member):
        """ returns the asocs for bands we're confirmed for """
        return super().get_queryset().filter(member=member, status=AssocStatusChoices.CONFIRMED)

    def add_gig_assocs(self, member):
        """ return the assocs for bands the member can create gigs for """
        return super().get_queryset().filter(
                            Q(member=member) & Q(status=AssocStatusChoices.CONFIRMED) & (
                                Q(member__is_superuser=True) | Q(is_admin=True) | Q(band__anyone_can_create_gigs=True)
                            )
                        )

class Assoc(models.Model):
    band = models.ForeignKey(Band, related_name="assocs", on_delete=models.CASCADE)
    member = models.ForeignKey("member.Member", verbose_name="member", related_name="assocs", on_delete=models.CASCADE)
    default_section = models.ForeignKey(Section, null=True, blank=True, related_name="default_assocs", on_delete=models.DO_NOTHING)

    status = models.IntegerField(choices=AssocStatusChoices.choices, default=AssocStatusChoices.NOT_CONFIRMED)

    is_admin = models.BooleanField(default=False)
    is_occasional = models.BooleanField(default=False)

    @property
    def is_confirmed(self):
        return self.status == AssocStatusChoices.CONFIRMED

    @property
    def section(self):
        if self.default_section is None:
            return self.band.sections.get(is_default=True)
        else:
            return self.default_section

    # default_section_index = ndb.IntegerProperty( default=None )

    is_multisectional = models.BooleanField( default = False )
    is_occasional = models.BooleanField( default = False )
    # commitment_number = ndb.IntegerProperty(default=0)
    # commitment_total = ndb.IntegerProperty(default=0)
    color = models.IntegerField(default=0)

    @property
    def colorval(self):
        return the_colors[self.color]

    email_me = models.BooleanField (default=True)
    hide_from_schedule = models.BooleanField (default=False)

    objects = models.Manager()
    member_assocs = MemberAssocManager()

    def __str__(self):
        return "{0} in {1}".format(self.member, self.band)



