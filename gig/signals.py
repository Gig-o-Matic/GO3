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
from gig.helpers import send_emails_from_plans
from lib.asyncsignal import async_receiver
from datetime import datetime
from django.utils import timezone

@receiver(pre_save, sender=Gig)
def set_date_time(sender, instance, **kwargs):
    t = instance.schedule_time
    instance.schedule_datetime = datetime.combine(instance.schedule_date, t) if t else instance.schedule_date

@async_receiver(post_save, sender=Gig)
def notify_new_gig(sender, instance, created, **kwargs):
    if created:
        # This has the side effect of creating plans for all members
        send_emails_from_plans(instance.member_plans, 'email/new_gig.md')
    else:
        send_emails_from_plans(instance.member_plans, 'email/edited_gig.md')

@receiver(pre_save, sender=Plan)
def update_plan_section(sender, instance, **kwargs):
    """ set the section to the plan_section, unless there isn't one - in that case use the member's default """
    instance.section = instance.plan_section or instance.assoc.section
