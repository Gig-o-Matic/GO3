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
from django_q.tasks import async_task

@receiver(post_save, sender=Gig)
def notify_new_gig(sender, instance, created, **kwargs):
    # This will have the side effect of creating plans for all members
    async_task('gig.helpers.send_email_from_gig', instance,
               'email/new_gig.md' if created else 'email/edited_gig.md')

@receiver(pre_save, sender=Plan)
def update_plan_section(sender, instance, **kwargs):
    """ set the section to the plan_section, unless there isn't one - in that case use the member's default """
    instance.section = instance.plan_section or instance.assoc.section
    if instance.status not in (Plan.StatusChoices.NO_PLAN, Plan.StatusChoices.DONT_KNOW):
        instance.snooze_until = None
