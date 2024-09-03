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
from django.apps import apps
from django.db import models
from django.db.models import Max, Q
from datetime import datetime, timedelta
from pytz import timezone

class BandStatusChoices(models.IntegerChoices):
    ACTIVE = 0, "Active"
    DORMANT = 1, "Dormant"
    DELETED = 2, "Deleted"

class AssocStatusChoices(models.IntegerChoices):
    NOT_CONFIRMED = 0, "Not Confirmed"
    CONFIRMED = 1, "Confirmed"
    INVITED = 2, "Invited"
    deprecated_alumni = 3,  # used to mean "alumni" but that has been deprecated
    PENDING = 4, "Pending"

def _get_active_bands():
    """ return list of bands that have made a gig in the last month """
    b = apps.get_model('band','Band')
    queryset = b.objects.filter(status=BandStatusChoices.ACTIVE)
    queryset = queryset.annotate(most_recent_gig=Max("gigs__created_date"), last_gig=Max("gigs__date"))
    now = datetime.now(timezone('UTC'))
    threshold =  now - timedelta(days=30)
    # find bands who have created a gig in the last [threshold] days, or have a gig in the future
    queryset = queryset.filter(Q(most_recent_gig__gt = threshold) | Q(last_gig__gt = now ))
    queryset = queryset.order_by('name')

    return list(queryset)

def _get_inactive_bands():
    """ return list of bands that haven't made a gig lately (or ever) """
    b = apps.get_model('band','Band')

    all = b.objects.all()
    active = _get_active_bands()

    # this is inefficient but using the union or ^ functions doesn't seem to work
    inactive = all.exclude(id__in=[x.id for x in active]).order_by('name')

    return list(inactive)

def _get_active_band_members():
    """ return list of bands that haven't made a gig lately (or ever) """
    a = apps.get_model('band','Assoc')

    active_assocs = a.objects.filter(band__in=_get_active_bands())
    active_members = list(set([a.member for a in active_assocs]))

    return active_members


