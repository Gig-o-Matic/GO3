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
from band.models import Band, Assoc
import datetime

class MemberPlanManager(models.Manager):
    def future_plans(self, member):
        return super().get_queryset().filter(assoc__member=member, 
                                             assoc__status=Assoc.StatusChoices.CONFIRMED,
                                             gig__date__gt=datetime.datetime.now())

class Plan(models.Model):
    """ Models a gig-o-matic plan """
    gig = models.ForeignKey("Gig", related_name="plans", on_delete=models.CASCADE)
    assoc = models.ForeignKey("band.Assoc", verbose_name="assoc", related_name="plans", on_delete=models.CASCADE)

    class StatusChoices(models.IntegerChoices):
        NO_PLAN = 0, "No Plan"
        DEFINITELY = 1, "Definitely"
        PROBABLY = 2, "Probably"
        DONT_KNOW = 3, "Don't Know"
        PROBABLY_NOT = 4, "Probably Not"
        CANT_DO_IT = 5, "Can't Do It"
        NOT_INTERESTED = 6, "Not Interested"

    status = models.IntegerField(choices=StatusChoices.choices, default=StatusChoices.NO_PLAN)

    feedback_value = models.IntegerField(null=True, blank=True)
    comment = models.CharField(max_length=200, blank=True, null=True)
    section = models.ForeignKey("band.Section", verbose_name="section", on_delete=models.SET_NULL, null=True, blank=True)
    last_update = models.DateTimeField(auto_now=True)
    snooze_until = models.DateTimeField(null=True, blank=True)

    objects = models.Manager()
    member_plans = MemberPlanManager()

    def __str__(self):
        return '{0} for {1} ({2})'.format(self.assoc.member.display_name, self.gig.title, Plan.StatusChoices(self.status).label)


class AbstractGig(models.Model):
    title = models.CharField(max_length=200)
    band = models.ForeignKey(Band, related_name="gigs", on_delete=models.CASCADE)

    details = models.TextField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)

    date = models.DateField()

    calltime = models.TimeField(null=True, blank=True)

    address = models.TextField(null=True, blank=True)
    class StatusOptions(models.IntegerChoices):
            UNKNOWN = 0
            CONFIRMED = 1
            CANCELLED = 2
            ASKING = 3
    status = models.IntegerField(choices=StatusOptions.choices, default=StatusOptions.UNKNOWN)

    @property
    def is_canceled(self):
        self.status=StatusOptions.CANCELLED

    @property
    def is_confirmed(self):
        self.status=StatusOptions.CONFIRMED

    # todo archive
    # archive_id = ndb.TextProperty( default=None )
    # is_archived = ndb.ComputedProperty(lambda self: self.archive_id is not None)

    is_private = models.BooleanField(default=False )    

    # todo what's this?
    # comment_id = ndb.TextProperty( default = None)

    creator = models.ForeignKey('member.Member', null=True, related_name="creator_gigs", on_delete=models.SET_NULL)

    invite_occasionals = models.BooleanField(default=True)
    was_reminded = models.BooleanField(default=False)
    hide_from_calendar = models.BooleanField(default=False)
    default_to_attending = models.BooleanField( default=False )

    trashed_date = models.DateTimeField( blank=True, null=True )

    @property
    def is_in_trash(self):
        return self.trashed_date is not None

    @property
    def member_plans(self):
        # find any members that don't have plans yet
        absent = self.band.assocs.exclude(id__in = self.plans.values_list('assoc',flat=True))
        Plan.objects.bulk_create(
            [Plan(gig=self, assoc=a) for a in absent]
        )
        # now that we have one for every member, return the list
        return self.plans


    def __str__(self):
        return self.title

class Gig(AbstractGig):

    # todo when a member leaves the band must set their contact_gigs to no contact. Nolo Contacto!
    contact = models.ForeignKey('member.Member', null=True, related_name="contact_gigs", on_delete=models.SET_NULL)
    setlist = models.TextField(null=True, blank=True)

    enddate = models.DateField(null=True, blank=True)

    settime = models.TimeField(null=True, blank=True)
    endtime = models.TimeField(null=True, blank=True)

    dress = models.TextField(null=True, blank=True)
    paid = models.TextField(null=True, blank=True)
    postgig = models.TextField(null=True, blank=True)

    leader = models.ForeignKey('member.Member', blank=True, null=True, related_name="leader_gigs", on_delete=models.SET_NULL)

    # todo manage these
    # trueenddate = ndb.ComputedProperty(lambda self: self.enddate if self.enddate else self.date)
    # sorttime = ndb.IntegerProperty( default=None )

    # todo what's this?
    # comment_id = ndb.TextProperty( default = None)


    rss_description = models.TextField( null=True, blank=True )
