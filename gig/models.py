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
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords
from band.models import Band, Assoc
from band.util import AssocStatusChoices
from .util import GigStatusChoices, PlanStatusChoices
from member.util import MemberStatusChoices
from django.utils import timezone
import datetime
import uuid


class GigsManager(models.Manager):
    def active(self):
        return super().filter(trashed_date__isnull=True)

    def trashed(self):
        return super().filter(trashed_date__isnull=False)

    def future(self):
        return self.active().filter(is_archived=False)


class MemberPlanManager(models.Manager):
    def all(self):
        """override the default all to order by section"""
        return super().order_by("section")

    def future_plans(self, member):
        return (
            super()
            .get_queryset()
            .filter(
                (Q(gig__enddate=None) & Q(gig__date__gt=timezone.now()))
                | Q(gig__enddate__gt=timezone.now()),
                assoc__member=member,
                assoc__status=AssocStatusChoices.CONFIRMED,
                gig__trashed_date__isnull=True,
                gig__is_archived=False,
            )
            .order_by("gig__date")
        )


class Plan(models.Model):
    """Models a gig-o-matic plan"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gig = models.ForeignKey("Gig", related_name="plans", on_delete=models.CASCADE)
    assoc = models.ForeignKey(
        "band.Assoc",
        verbose_name="assoc",
        related_name="plans",
        on_delete=models.CASCADE,
    )

    status = models.IntegerField(
        choices=PlanStatusChoices.choices, default=PlanStatusChoices.NO_PLAN
    )

    @property
    def status_string(self):
        return PlanStatusChoices(self.status).label

    @property
    def attending(self):
        return self.status in [PlanStatusChoices.DEFINITELY, PlanStatusChoices.PROBABLY]

    feedback_value = models.IntegerField(null=True, blank=True)

    @property
    def feedback_string(self):
        if self.feedback_value and self.gig.band.plan_feedback:
            return self.gig.band.plan_feedback[self.feedback_value - 1]
        else:
            return ""

    comment = models.CharField(max_length=200, blank=True, null=True)

    # plan_section holds the section override for this particular plan. it may be set by the pre_delete signal on section
    plan_section = models.ForeignKey(
        "band.Section",
        related_name="plansections",
        verbose_name="plan_section",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
    )

    # section is the actual section the member will use for this plan. It is updated by a presave signal on the plan,
    # and by the code that sets the default section for an assoc, or pre_delete signal on section
    section = models.ForeignKey(
        "band.Section",
        related_name="sections",
        verbose_name="section",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
    )

    last_update = models.DateTimeField(auto_now=True)
    snooze_until = models.DateTimeField(null=True, blank=True)

    objects = models.Manager()
    member_plans = MemberPlanManager()

    def __str__(self):
        return "{0} for {1} ({2})".format(
            self.assoc.member.display_name,
            self.gig.title,
            PlanStatusChoices(self.status).label,
        )


class AbstractEvent(models.Model):

    class Meta:
        abstract = True

    title = models.CharField(max_length=200)
    band = models.ForeignKey(
        Band,
        related_name="%(class)ss",
        related_query_name="%(class)ss",
        on_delete=models.CASCADE,
    )

    details = models.TextField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)

    date = models.DateTimeField()
    datenotes = models.TextField(null=True, blank=True)

    address = models.TextField(null=True, blank=True)
    status = models.IntegerField(
        choices=GigStatusChoices.choices, default=GigStatusChoices.UNKNOWN
    )

    @property
    def is_canceled(self):
        self.status = GigStatusChoices.CANCELLED

    @property
    def is_confirmed(self):
        self.status = GigStatusChoices.CONFIRMED

    def status_string(self):
        return [_("Unconfirmed"), _("Confirmed!"), _("Cancelled!"), _("Asking")][
            self.status
        ]  # pylint: disable=invalid-sequence-index

    is_archived = models.BooleanField(default=False)

    is_private = models.BooleanField(default=False)

    # todo what's this?
    # comment_id = ndb.TextProperty( default = None)

    creator = models.ForeignKey(
        "member.Member",
        null=True,
        related_name="creator_gigs",
        on_delete=models.SET_NULL,
    )

    invite_occasionals = models.BooleanField(default=True)
    was_reminded = models.BooleanField(default=False)
    hide_from_calendar = models.BooleanField(default=False)
    default_to_attending = models.BooleanField(default=False)

    trashed_date = models.DateTimeField(blank=True, null=True)

    @property
    def is_in_trash(self):
        return self.trashed_date is not None

    objects = GigsManager()

    def __str__(self):
        return self.title


class Gig(AbstractEvent):

    # todo when a member leaves the band must set their contact_gigs to no contact. Nolo Contacto!
    contact = models.ForeignKey(
        "member.Member",
        null=True,
        related_name="contact_gigs",
        on_delete=models.SET_NULL,
    )
    setlist = models.TextField(null=True, blank=True)

    setdate = models.DateTimeField(null=True, blank=True)
    enddate = models.DateTimeField(null=True, blank=True)

    dress = models.TextField(null=True, blank=True)
    paid = models.TextField(null=True, blank=True)
    postgig = models.TextField(null=True, blank=True)

    leader = models.ForeignKey(
        "member.Member",
        blank=True,
        null=True,
        related_name="leader_gigs",
        on_delete=models.SET_NULL,
    )

    # todo manage these
    # trueenddate = ndb.ComputedProperty(lambda self: self.enddate if self.enddate else self.date)
    # sorttime = ndb.IntegerProperty( default=None )

    # todo what's this?
    # comment_id = ndb.TextProperty( default = None)

    rss_description = models.TextField(null=True, blank=True)

    # for use in calfeeds
    cal_feed_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)

    # We need to exclude the band, lest the reverse query in Band conflict
    # We need to exclude the cal_feed_id, because we want it to be unique and the history table gets a copy of every change
    history = HistoricalRecords(excluded_fields=["band", "cal_feed_id"])

    @property
    def member_plans(self):
        """if this gig is not archived, find any members that don't have plans yet. This is called whenever a new gig is created
        through the signaling system, or when a member joins a band from the assoc signal.
        """
        if self.is_archived is False:
            absent = (
                self.band.assocs.exclude(
                    id__in=self.plans.values_list("assoc", flat=True)
                )
                .filter(member__status=MemberStatusChoices.ACTIVE)
                .filter(status=AssocStatusChoices.CONFIRMED)
            )
            # Plan.objects.bulk_create(
            #     [Pn(glaig=self, assoc=a, section=a.band.sections.get(is_default=True)) for a in absent]
            # )
            # can't use bulk_create because it doesn't send signals
            # TODO is there a more efficient way?
            s = self.band.sections.get(is_default=True)
            for a in absent:
                Plan.objects.create(gig=self, assoc=a, section=s)

        # if this is an archived gig, return all the plans, otherwise just those for active members
        plans = self.plans  # pylint: disable=no-member
        if self.is_archived:
            return plans
        else:
            return plans.filter(
                assoc__member__status=MemberStatusChoices.ACTIVE
            ).filter(assoc__status=AssocStatusChoices.CONFIRMED)


class GigComment(models.Model):
    gig = models.ForeignKey("Gig", related_name="comments", on_delete=models.CASCADE)
    member = models.ForeignKey(
        "member.Member",
        verbose_name="member",
        related_name="comments",
        on_delete=models.CASCADE,
    )
    text = models.TextField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)
