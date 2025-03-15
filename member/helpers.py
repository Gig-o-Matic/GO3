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
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import get_object_or_404, redirect
from datetime import timedelta
from member.models import Member
from lib.email import prepare_email, send_messages_async
from lib.caldav import make_calfeed, save_calfeed, get_calfeed
from django.core.exceptions import ValidationError
from django.conf import settings
from band.helpers import do_delete_assoc
from member.util import MemberStatusChoices
from member.models import Member

from django.utils.translation import gettext_lazy as _

def superuser_required(func):
    def decorated(request, pk, *args, **kw):
        if not request.user.is_superuser:
            return HttpResponseForbidden()

        return func(request, pk, *args, **kw)
    return decorated


@login_required
def motd_seen(request, pk):
    """ note that we've seen the motd """
    if request.user.id != pk:
        raise PermissionError('trying to mark MOTD seen for another user')

    request.user.motd_dirty = False
    request.user.save()

    return HttpResponse()


@login_required
def send_test_email(request):
    template = 'email/email_test.md'
    send_messages_async([prepare_email(request.user.as_email_recipient(), template)])

    return HttpResponse(_("test email sent"))


@login_required
def delete_member(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.user != member and request.user.is_superuser is False:
        return HttpResponseForbidden()
    # member.delete()
    # instead of deleting the member, anonymize
    member.status = MemberStatusChoices.DELETED
    member.email = "assoc_{0}@gig-o-matic.com".format(member.id)
    member.username = _("former member")
    member.nickname = ''
    member.phone = ''
    member.statement = ''
    member.set_unusable_password()
    member.save()

    the_assocs = member.assocs.all()
    for a in the_assocs:
        do_delete_assoc(a) # will set to "ALUMNI"

    if request.user.is_superuser is False:
        logout(request)

    return redirect('home')

def send_invite_async(invite):
    context = {
        'new': (Member.objects.filter(email=invite.email).count() == 0),
        'invite_id': invite.id,
        'band_name': invite.band.name if invite.band else None
    }
    template = 'email/invite.md' if invite.band else 'email/signup.md'
    send_messages_async([prepare_email(invite.as_email_recipient(), template, context)])


def send_email_conf(confirmation):
    context = {
        'confirmation_id': confirmation.id,
    }
    template = 'email/email_confirmation.md'
    send_messages_async([prepare_email(confirmation.as_email_recipient(), template, context)])


def prepare_calfeed(member):
    # we want the gigs as far back as a year ago
    date_earliest = timezone.now() - timedelta(days=365)
    the_plans = member.calendar_plans.filter(gig__date__gt=date_earliest)
    the_gigs = [p.gig for p in the_plans]
    cf = make_calfeed(member, the_gigs,
                      member.preferences.language, member.cal_feed_id)
    return cf


def update_member_calfeed(id):
    m = Member.objects.get(id=id)
    cf = prepare_calfeed(m)
    save_calfeed(m.cal_feed_id, cf)

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

    return HttpResponse(tf,content_type='text/calendar')

def go2_id_calfeed(request, go2_id):
    try:
        member = Member.objects.get(go2_id=go2_id)
        return calfeed(request, member.cal_feed_id)
    except(Member.DoesNotExist):
        hr = HttpResponse()
        hr.status_code = 404
        return hr

# helpers to define member permissions for various things
def has_band_admin(user, band):
    return user and user.is_superuser or band.is_admin(user)

def has_manage_gig_permission(user, band):
    return user and (
        has_band_admin(user, band) or
        (band.has_member(user) and band.anyone_can_manage_gigs))

def has_create_gig_permission(user, band):
    return user and (
        has_band_admin(user, band) or
        (band.has_member(user) and band.anyone_can_create_gigs))

def has_comment_permission(user, gig):
    return user and (
        user.is_superuser or gig.band.has_member(user))

def has_manage_band_permission(user, band):
    return user and has_band_admin(user,band)
