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

import logging
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound
from .models import Band, Assoc, Section
from gig.helpers import update_plan_default_section
from member.models import Member
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from band.util import AssocStatusChoices


def member_can_edit_band(member, band):
    return member.is_superuser or (Assoc.objects.filter(member=member, band=band, is_admin=True).count() == 1)

def assoc_editor_required(func):
    def decorated(request, ak, *args, **kw):
        a = get_object_or_404(Assoc, pk=ak)
        is_self = (request.user == a.member)
        is_band_admin = member_can_edit_band(request.user, a.band)
        if not (is_self or is_band_admin or request.user.is_superuser):
            return HttpResponseForbidden()

        return func(request, a, *args, **kw)
    return decorated


@login_required
@assoc_editor_required
def set_assoc_tfparam(request, a):
    """ set a true/false parameter on an assoc """
    is_self = (request.user == a.member)
    for param, value in request.POST.items():
        # A user cannot set their own admin status, but a superuser can do anything
        if param == 'is_admin' and is_self and not request.user.is_superuser:
            continue

        if hasattr(a, param):
            setattr(a, param, True if value == 'true' else False)
        else:
            logging.error(f"Trying to set an assoc property that does not exist: {param}")
    a.save()

    return HttpResponse(status=204)


@login_required
@assoc_editor_required
def set_assoc_section(request, a, sk):
    """ set a default section on an assoc """
    if sk == 0:
        s = None
    else:
        s = get_object_or_404(Section, pk=sk)
        if s.band != a.band:
            logging.error(f"Trying to set a section that is not part of band: {s} for {a.band}")
            return HttpResponseNotFound()

    a.default_section = s
    a.save()

    return HttpResponse(status=204)


@login_required
@assoc_editor_required
def set_assoc_color(request, a, colorindex):
    """ set a default section on an assoc """
    a.color = colorindex
    a.save()

    return render(request, 'member/color.html', {'assoc': a})


@login_required
def join_assoc(request, bk, mk):
    b = get_object_or_404(Band, pk=bk)

    if (mk == request.user.id):
        m = request.user
    else:
        m = get_object_or_404(Member, pk=mk)

    # todo make sure this is us, or we're superuser, or band_admin
    is_self = (request.user == m)
    is_super = (request.user.is_superuser)
    # TODO: Should band admins actually be able to create pending associations?
    is_band_admin = Assoc.objects.filter(
        member=request.user, band=b, is_admin=True).count() == 1
    if not (is_self or is_super or is_band_admin):
        raise PermissionError(
            'tying to create an assoc which is not owned by user {0}'.format(request.user.username))

    # OK, create the assoc
    Assoc.objects.get_or_create(
        band=b, member=m, status=AssocStatusChoices.PENDING)

    return HttpResponse(status=204)


@login_required
@assoc_editor_required
def delete_assoc(request, a):
    a.delete()

    return HttpResponse(status=204)


@login_required
def confirm_assoc(request, ak):
    a = get_object_or_404(Assoc, pk=ak)

    is_super = (request.user.is_superuser)
    is_band_admin = (Assoc.objects.filter(member=request.user,
                                          band=a.band, is_admin=True).count() == 1)
    if not (is_super or is_band_admin):
        logging.error(f'Trying to confirm an assoc which is not admin by user {request.user.username}')
        return HttpResponseForbidden()

    # OK, confirm the assoc
    a.status = AssocStatusChoices.CONFIRMED
    a.save()

    return HttpResponse()


def set_calfeeds_dirty(band):
    """ called from gig post_save signal - when gig is updated, set calfeeds dirty for all members """
    Member.objects.filter(assocs__band=band).update(cal_feed_dirty=True)
