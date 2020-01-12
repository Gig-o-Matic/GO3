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

from django.http import HttpResponse
from .models import Band, Assoc, Section
from member.models import Member
from django.contrib.auth.decorators import login_required

@login_required
def set_assoc_tfparam(request, ak, param, truefalse):
    """ set a true/false parameter on an assoc """
    a = Assoc.objects.filter(id=ak)

    if len(a) != 1:
        raise ValueError('altering an assoc that does not exist')
    else:
        a=a[0]

        if request.user != a.member and not request.user.is_superuser:
            raise PermissionError('tying to alter an assoc which is not owned by user {0}'.format(request.user.username))

        if hasattr(a, param):
            setattr(a, param, True if truefalse=='true' else False)
            a.save()
        else:
            raise ValueError('trying to set an assoc parameter that does not exist: {0}'.format(param))
    return HttpResponse()


@login_required
def set_assoc_section(request, ak, sk):
    """ set a default section on an assoc """
    a = Assoc.objects.filter(id=ak)

    # todo make sure this is us, or we're superuser
    if len(a) != 1:
        raise ValueError('altering an assoc that does not exist')
    else:
        a=a[0]

        if request.user != a.member and not request.user.is_superuser:
            raise PermissionError('tying to alter an assoc which is not owned by user {0}'.format(request.user.username))

        if sk == 0:
            s = None
        else:
            s=Section.objects.filter(id=sk)
            if len(s) != 1:
                raise ValueError('setting a section that does not exist')
            s=s[0]
            if s.band != a.band:
                raise ValueError('setting a section that is not part of the band')

        a.default_section=s
        a.save()
    return HttpResponse()


@login_required
def set_assoc_color(request, ak, colorindex):
    """ set a default section on an assoc """
    a = Assoc.objects.filter(id=ak)

    # todo make sure this is us, or we're superuser
    if len(a) != 1:
        raise ValueError('altering an assoc that does not exist')
    else:
        a=a[0]

        if request.user != a.member and not request.user.is_superuser:
            raise PermissionError('tying to alter an assoc which is not owned by user {0}'.format(request.user.username))

        a.color = colorindex
        a.save()

    return HttpResponse()


@login_required
def join_assoc(request, bk, mk):
    b = Band.objects.get(id=bk)

    if (mk == request.user.id):
        m = request.user
    else:
        m = Member.objects.get(id=mk)

    # todo make sure this is us, or we're superuser, or band_admin
    is_self = (request.user == m)
    is_super = (request.user.is_superuser)
    is_band_admin = Assoc.objects.filter(member=request.user, band=b, is_admin=True).count() == 1
    if not (is_self or is_super or is_band_admin):
        raise PermissionError('tying to create an assoc which is not owned by user {0}'.format(request.user.username))

    # OK, create the assoc
    a = Assoc.objects.get_or_create(band=b, member=m)

    return HttpResponse()

@login_required
def delete_assoc(request, ak):
    a = Assoc.objects.get(id=ak)

    # todo make sure this is us, or band_admin, or we're superuser
    is_self = (request.user == a.member)
    is_super = (request.user.is_superuser)
    is_band_admin = (Assoc.objects.filter(member=request.user, band=a.band, is_admin=True).count() == 1)
    if not (is_self or is_super or is_band_admin):
        raise PermissionError('tying to delete an assoc which is not owned by user {0}'.format(request.user.username))
    
    a.delete()

    return HttpResponse()

@login_required
def confirm_assoc(request, ak):
    a = Assoc.objects.get(id=ak)

    # todo make sure this is a band_admin, or we're superuser
    is_super = (request.user.is_superuser)
    is_band_admin = (Assoc.objects.filter(member=request.user, band=a.band, is_admin=True).count() == 1)
    if not (is_super or is_band_admin):
        raise PermissionError('tying to confirm an assoc which is not admin by user {0}'.format(request.user.username))

    # OK, confirm the assoc
    a.status = Assoc.StatusChoices.CONFIRMED
    a.save()

    return HttpResponse()
