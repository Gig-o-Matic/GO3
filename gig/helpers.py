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
from django.utils.formats import date_format, time_format
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import template_localtime
from .models import Gig, Plan
from band.models import Section, AssocStatusChoices
from member.helpers import prepare_email
from lib.email import send_messages_async
from lib.translation import join_trans

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

def date_format_func(dt, fmt):
    # Returns lambdas that the template will evaluate in the correct
    # language context
    return lambda: date_format(template_localtime(dt), fmt) if dt else _('not set')

def date_diff(latest, previous):
    if latest and previous and latest.date() == previous.date():
        return (date_format_func(latest, 'TIME_FORMAT'),
                date_format_func(previous, 'TIME_FORMAT'))
    return (date_format_func(latest, 'SHORT_DATETIME_FORMAT'),
            date_format_func(previous, 'SHORT_DATETIME_FORMAT'))

def generate_changes(latest, previous):
    if not previous:
        return []

    changes = []
    diff = latest.diff_against(previous)
    if 'status' in diff.changed_fields:
        # The historical copy only gets properties, it appears
        changes.append((_('Status'), Gig.status_string(latest), Gig.status_string(previous)))
    if 'date' in diff.changed_fields:
        changes.append((_('Call Time'), *date_diff(latest.date, previous.date)))
    if 'setdate' in diff.changed_fields:
        changes.append((_('Set Time'), *date_diff(latest.setdate, previous.setdate)))
    if 'enddate' in diff.changed_fields:
        changes.append((_('End Time'), *date_diff(latest.enddate, previous.enddate)))
    if 'contact' in diff.changed_fields:
        changes.append((_('Contact'),
                       latest.contact.display_name if latest.contact else '??',
                       previous.contact.display_name if previous.contact else '??'))
    if set(diff.changed_fields) - {'status', 'date', 'setdate', 'enddate'}:
        changes.append((_('Details'), _('(See below.)'), None))
    return changes

def email_from_plan(plan, template):
    gig = plan.gig
    with timezone.override(gig.band.timezone):
        latest_record = gig.history.latest()
        changes = generate_changes(latest_record, latest_record.prev_record)
        member = plan.assoc.member
        contact_name, contact_email = ((contact.display_name, contact.email)
                                       if (contact := gig.contact) else ('??', None))
        context = {
            'gig': gig,
            'changes': changes,
            'changes_title': join_trans(_(', '), (c[0] for c in changes)),
            'contact_name': contact_name,
            'plan': plan,
            'status': plan.status,
            'status_label': Plan.StatusChoices(plan.status).label,
            **Plan.StatusChoices.__members__,
        }
        return prepare_email(member, template, context, reply_to=[contact_email])

def send_emails_from_plans(plans_query, template):
    contactable = plans_query.filter(assoc__status=AssocStatusChoices.CONFIRMED,
                                     assoc__email_me=True)
    send_messages_async(email_from_plan(p, template) for p in contactable)

def send_email_from_gig(gig, template):
    send_emails_from_plans(gig.member_plans, template)

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
