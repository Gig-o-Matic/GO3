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

import datetime
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Plan
from band.models import Section, AssocStatusChoices
from member.helpers import prepare_email
from lib.email import send_messages_async

@login_required
def update_plan(request, pk, val):
    """ set value of plan """
    plan = Plan.objects.get(id=pk)
    plan.status = val
    plan.save()
    return HttpResponse()

@login_required
def update_plan_feedback(request, pk, val):
    """ set value of plan """
    plan = Plan.objects.get(id=pk)
    plan.feedback_value = val
    plan.save()
    return HttpResponse()

@login_required
def update_plan_comment(request, pk):
    """ set value of plan """
    plan = Plan.objects.get(id=pk)
    plan.comment = request.POST['value']
    plan.save()
    return HttpResponse()

@login_required
def update_plan_section(request, pk, val):
    """ set section for this plan """
    plan = Plan.objects.get(id=pk)
    plan.plan_section = Section.objects.get(id=val)
    plan.save()
    return HttpResponse()


# @login_required
def update_plan_default_section(assoc):
    """
    the default section of the member assoc has changed, so update any plans that aren't overriding
    """
    Plan.objects.filter(assoc=assoc, plan_section=None).update(section=assoc.default_section)

def get_confirm_urls(member, gig):
    return {'yes_url': 'http://example.com/yes', 'no_url': 'http://example.com/no', 'snooze_url': 'http://example.com/snooze'}

def email_from_plan(plan, template):
    gig = plan.gig
    member = plan.assoc.member
    contact_name, contact_email = ((contact.display_name, contact.email)
                                   if (contact := gig.contact) else ('??', None))
    context = {
        'gig': gig,
        'contact_name': contact_name,
        **get_confirm_urls(member, gig)
    }
    return prepare_email(member, template, context, reply_to=[contact_email])

def send_emails_from_plans(plans_query, template):
    contactable = plans_query.filter(assoc__status=AssocStatusChoices.CONFIRMED,
                                     assoc__email_me=True)
    send_messages_async(email_from_plan(p, template) for p in contactable)

def send_reminder_email(gig):
    undecided = gig.member_plans.filter(status__in=(Plan.StatusChoices.NO_PLAN, Plan.StatusChoices.DONT_KNOW))
    send_emails_from_plans(undecided, 'email/gig_reminder.md')

def send_snooze_reminders():
    """
    Send a reminder for all plans with a snooze_until in the next day and a gig
    date in the future.  Set the snooze_until property of all such plans to None,
    to so we don't send another reminder in the future.
    """
    now = datetime.datetime.now(tz=timezone.get_current_timezone())
    next_day = now + datetime.timedelta(days=1)
    unsnooze = Plan.objects.filter(snooze_until__isnull=False,
                                   snooze_until__lte=next_day,
                                   gig__date__gt=now)
    send_emails_from_plans(unsnooze, 'email/gig_reminder.md')
    unsnooze.update(snooze_until=None)
