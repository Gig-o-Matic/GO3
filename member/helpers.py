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

from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone, translation
from django.contrib.auth.decorators import login_required
from markdown import markdown
from datetime import timedelta

from gig.models import Gig, Plan
from member.models import Member

from lib.email import DEFAULT_SUBJECT, SUBJECT, send_messages_async
from lib.caldav import make_calfeed, save_calfeed, get_calfeed
from django.core.exceptions import ValidationError
from django.conf import settings


@login_required
def motd_seen(request, pk):
    """ note that we've seen the motd """
    if request.user.id != pk:
        raise PermissionError('trying to mark MOTD seen for another user')

    request.user.motd_dirty = False
    request.user.save()

    return HttpResponse()


def prepare_email(member, template, context=None, **kw):
    if not context:
        context = dict()
    context['member'] = member

    with translation.override(member.preferences.language):
        text = render_to_string(template, context).strip()
    if text.startswith(SUBJECT):
        subject, text = [t.strip() for t in text[len(SUBJECT):].split('\n', 1)]
    else:
        subject = DEFAULT_SUBJECT
    html = markdown(text, extensions=['nl2br'])

    message = EmailMultiAlternatives(
        subject, text, to=[member.email_line], **kw)
    message.attach_alternative(html, 'text/html')
    return message


def send_invite(invite):
    new = (Member.objects.filter(email=invite.email).count() == 0)
    send_messages_async([prepare_email(invite, 'email/invite.md', {'new': new})])


def prepare_calfeed(member):
    # we want the gigs as far back as a year ago
    date_earliest = timezone.now() - timedelta(days=365)

    filter_args = {
        "assoc__member_id": member.id,
        "gig__date__gt": date_earliest,
    }

    if member.preferences.calendar_show_only_confirmed:
        filter_args["gig__status"] = Gig.StatusOptions.CONFIRMED

    if member.preferences.calendar_show_only_committed:
        filter_args["status__in"] = [
            Plan.StatusChoices.DEFINITELY, Plan.StatusChoices.PROBABLY]

    the_plans = Plan.objects.filter(**filter_args)

    if member.preferences.hide_canceled_gigs:
        the_plans = the_plans.exclude(gig__status=Gig.StatusOptions.CANCELLED)

    the_gigs = [p.gig for p in the_plans]
    cf = make_calfeed(member, the_gigs,
                      member.preferences.language, member.cal_feed_id)
    return cf

def update_all_calfeeds():
    """ request handler for updating cached calfeeds - should be called on a schedule """
    if settings.DYNAMIC_CALFEED:
        # if we're generating calfeeds dynamically, don't update the disk cache
        Member.objects.filter(cal_feed_dirty=True).update(cal_feed_dirty=False)
        return

    members = Member.objects.filter(cal_feed_dirty=True)
    for m in members:
        cf = prepare_calfeed(m)
        save_calfeed(m.cal_feed_id, cf)
    members.update(cal_feed_dirty=False)


def calfeed(request, pk):
    try:
        if settings.DYNAMIC_CALFEED:
            # if the dynamic calfeed is set, just create the calfeed right now and return it
            tf = prepare_calfeed(Member.objects.get(cal_feed_id=pk))
        else:
            # if using the task queue, get the calfeed from the disk cache
            tf = get_calfeed(pk)
    except (ValueError, ValidationError):
        hr = HttpResponse()
        hr.status_code = 404
        return hr

    return HttpResponse(tf)
