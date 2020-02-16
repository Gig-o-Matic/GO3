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
from .helpers import get_confirm_urls
from lib.email import send_messages_async
from member.helpers import prepare_email
from datetime import datetime
from django.utils import timezone

@receiver(pre_save, sender=Gig)
def set_date_time(sender, instance, **kwargs):
    t = instance.schedule_time
    instance.schedule_datetime = datetime.combine(instance.schedule_date, t) if t else instance.schedule_date

@receiver(post_save, sender=Gig)
def new_gig_handler(sender, instance, created, **kwargs):
    """ if this is a new gig, make sure there's a plan for every member """
    x = instance.member_plans

@receiver(post_save, sender=Gig)
def notify_new_gig(sender, instance, created, **kwargs):
    if not created:
        return

    contact_name, contact_email = ((contact.display_name, contact.email)
                                   if (contact := instance.contact)
                                   else ('??', None))
    emails = [prepare_email(a.member,
                            'email/new_gig.md',
                            {
                                'gig': instance,
                                'contact_name': contact_name,
                                **get_confirm_urls(a.member, instance)
                            },
                            reply_to=[contact_email])
              for a in instance.band.confirmed_assocs if a.email_me]
    send_messages_async(emails)

@receiver(pre_save, sender=Plan)
def update_plan_section(sender, instance, **kwargs):
    """ set the section to the plan_section, unless there isn't one - in that case use the member's default """
    instance.section = instance.plan_section or instance.assoc.section
