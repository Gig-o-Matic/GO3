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

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Gig, Plan
from .util import PlanStatusChoices
from gig.helpers import send_emails_from_plans
from band.helpers import set_calfeeds_dirty
from django_q.tasks import async_task
from go3.settings import IN_ETL


@receiver(post_save, sender=Gig)
def create_member_plans(sender, instance, created, **kwargs):
    """makes sure every member has a plan set for a newly created gig"""
    if created:
        _ = instance.member_plans


@receiver(post_save, sender=Gig)
def set_calfeed_dirty(sender, instance, created, **kwargs):
    if IN_ETL is False:
        async_task("band.helpers.set_calfeeds_dirty", instance.band)


@receiver(pre_save, sender=Plan)
def update_plan_section(sender, instance, **kwargs):
    """set the section to the plan_section, unless there isn't one - in that case use the member's default"""
    instance.section = instance.plan_section or instance.assoc.section

    # if our answer changes from DONT_KNOW to anything, make sure we don't have a snooze reminder set
    if instance.status not in (PlanStatusChoices.NO_PLAN, PlanStatusChoices.DONT_KNOW):
        instance.snooze_until = None
