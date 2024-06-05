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
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.utils.formats import date_format, time_format
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import template_localtime, now
from django.db.models import Q
from .models import Gig, Plan
from .util import PlanStatusChoices
from band.models import Section, Assoc, AssocStatusChoices
from stats.tasks import register_sent_emails
from lib.email import prepare_email, send_messages_async
from lib.translation import join_trans
from django_q.tasks import async_task
from datetime import timedelta
from collections import Counter
import uuid
import calendar

def band_editor_required(func):
    def decorated(request, pk, *args, **kw):
        g = get_object_or_404(Gig, pk=pk)
        if not g.band.is_editor(request.user):
            return HttpResponseForbidden()
        return func(request, g, *args, **kw)
    return decorated

def plan_editor_required(func):
    def decorated(request, pk, *args, **kw):
        p = get_object_or_404(Plan, pk=pk)
        is_self = (request.user == p.assoc.member)
        is_band_admin = Assoc.objects.filter(
            member=request.user, band=p.assoc.band, is_admin=True).count() == 1
        if not (is_self or is_band_admin or request.user.is_superuser):
            return HttpResponseForbidden()

        return func(request, p, *args, **kw)
    return decorated


@login_required
@plan_editor_required
def update_plan(request, plan, val):
    plan.status = val
    plan.save()
    return render(request, 'gig/plan_icon.html', {'plan_value': val})

@login_required
@plan_editor_required
def update_plan_feedback(request, plan, val):
    plan.feedback_value = val
    plan.save()
    return HttpResponse(status=204)

@login_required
@plan_editor_required
def update_plan_comment(request, plan):
    plan.comment = request.POST['value'][:200]
    plan.save()
    return HttpResponse()

@login_required
@plan_editor_required
def update_plan_section(request, plan, val):
    plan.plan_section = get_object_or_404(Section, pk=val)
    plan.save()
    return HttpResponse(status=204)


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
    if latest and previous and latest.date == previous.date:
        return (date_format_func(latest, 'TIME_FORMAT')(),
                date_format_func(previous, 'TIME_FORMAT')())
    return (date_format_func(latest, 'SHORT_DATETIME_FORMAT')(),
            date_format_func(previous, 'SHORT_DATETIME_FORMAT')())

def generate_changes(latest, previous):
    if not previous:
        return []

    changes = []
    diff = latest.diff_against(previous)
    if 'status' in diff.changed_fields:
        # The historical copy only gets properties, it appears
        changes.append((_('Status'), Gig.status_string(latest), Gig.status_string(previous)))
    if 'contact' in diff.changed_fields:
        changes.append((_('Contact'),
                       latest.contact.display_name if latest.contact else '??',
                       previous.contact.display_name if previous.contact else '??'))

    # when dates were simpler this code used to put text into the email saying what the times had changed to. But since
    # we have full-day events and all kinds of permutations, let's just skip this and readdress another time
    # if 'date' in diff.changed_fields:
    #     changes.append((_('Call Time'), *date_diff(latest.date, previous.date)))
    # if 'setdate' in diff.changed_fields:
    #     changes.append((_('Set Time'), *date_diff(latest.setdate, previous.setdate)))
    # if 'enddate' in diff.changed_fields:
    #     changes.append((_('End Time'), *date_diff(latest.enddate, previous.enddate)))
        
    check = [x in diff.changed_fields for x in ['is_full_day', 'date', 'setdate', 'senddate', 'datenotes']]
    if True in check:
        changes.append((_('Date/Time'), _('(See below.)'), None))

    if 'address' in diff.changed_fields:
        changes.append((_('Address'), _('(See below.)'), None))

    if 'postgig' in diff.changed_fields:
        changes.append((_('Post-gig Plans'), _('(See below.)'), None))

    if 'details' in diff.changed_fields:
        changes.append((_('Details'), _('(See below.)'), None))
    
    if 'dress' in diff.changed_fields:
        changes.append((_('What To Wear'), _('(See below.)'), None))

    return changes

def is_single_day(gig):
    end = gig.enddate or gig.setdate
    if not end:
        return True
    return (end - gig.date) < datetime.timedelta(days=1)

def email_from_plan(plan, template, dates=None):
    gig = plan.gig
    with timezone.override(gig.band.timezone):
        latest_record = gig.history.latest()
        changes = generate_changes(latest_record, latest_record.prev_record)
        member = plan.assoc.member
        contact_name, contact_email = ((gig.contact.display_name, gig.contact.email)
                                       if gig.contact else ('??', None))
        context = {
            'gig': gig,
            'changes': changes,
            'changes_title': join_trans(_(', '), (c[0] for c in changes)),
            'single_day': is_single_day(gig),
            'contact_name': contact_name,
            'plan': plan,
            'status': plan.status,
            'status_label': PlanStatusChoices(plan.status).label,
            'dates': dates,
            **PlanStatusChoices.__members__,
        }
        return prepare_email(member.as_email_recipient(), template, context, reply_to=[contact_email])

def send_emails_from_plans(plans_query, template, dates=None):
    contactable = plans_query.filter(assoc__status=AssocStatusChoices.CONFIRMED,
                                     assoc__email_me=True)
    # if the plan is for a gig that did not invite occasionals, select only members that are not
    # occasional
    contactable = contactable.filter(Q(gig__invite_occasionals=True) | Q(assoc__is_occasional=False))
    send_messages_async(email_from_plan(p, template, dates) for p in contactable)

    # do this as a counter even though any specific call of this will be for a single band.
    if contactable.count():
        register_sent_emails(contactable.first().gig.band, contactable.count())

def send_email_from_gig(gig, template, dates=None):
    send_emails_from_plans(gig.member_plans, template, dates)

def send_reminder_email(gig):
    undecided = gig.member_plans.filter(status__in=(PlanStatusChoices.NO_PLAN, PlanStatusChoices.DONT_KNOW))
    send_emails_from_plans(undecided, 'email/gig_reminder.md')


def notify_new_gig(gig, created, dates=None):
    if dates:
        async_task('gig.helpers.send_email_from_gig', gig, 'email/new_gig_series.md', dates=dates)
    else:
        async_task('gig.helpers.send_email_from_gig', gig,
                'email/new_gig.md' if created else 'email/edited_gig.md')

@login_required
@band_editor_required
def gig_untrash(request, gig):
    gig.trashed_date = None
    gig.save()
    return redirect('gig-detail', pk=gig.id)

@login_required
@band_editor_required
def gig_trash(request, gig):
    gig.trashed_date = now()
    gig.save()
    return redirect('gig-detail', pk=gig.id)

@login_required
@band_editor_required
def gig_archive(request, gig):
    gig.is_archived = True
    gig.save()
    return redirect('gig-detail', pk=gig.id)

@login_required
@band_editor_required
def gig_remind(request, gig):
    gig.was_reminded = True
    gig.save()
    send_reminder_email(gig)
    return HttpResponse()


def create_gig_series(the_gig, number_to_copy, period):
    """ create a series of copies of a gig spaced out over time """

    if not number_to_copy:
        return

    last_date = the_gig.date
    if period == 'day':
        delta = timedelta(days=1)
    elif period == 'week':
        delta = timedelta(weeks=1)
    else:
        day_of_month = last_date.day
        
    set_delta = (the_gig.setdate - the_gig.date) if the_gig.setdate else None
    end_delta = (the_gig.enddate - the_gig.date) if the_gig.enddate else None

    the_dates = [the_gig.date]

    for _ in range(1, number_to_copy):
        if period == 'day' or period == 'week':
            last_date = last_date + delta
        else:
            yr = last_date.year
            mo = last_date.month+1
            if mo > 12:
                mo = 1
                yr += 1
            # figure out last day of next month
            last_date = last_date.replace(month=mo, day=min(calendar.monthrange(yr,mo)[1], day_of_month), year=yr)

        the_gig.date = last_date
        
        if set_delta is not None:
            the_gig.setdate = the_gig.date + set_delta

        if end_delta is not None:
            the_gig.enddate = the_gig.date + end_delta

        the_gig.id = None
        the_gig.pk = None
        the_gig._state.adding = True
        the_gig.cal_feed_id = uuid.uuid4()
        the_gig.save()
        the_dates.append(the_gig.date)
    
    # return the list of dates for all the gigs
    return the_dates