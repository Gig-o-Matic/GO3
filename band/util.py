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
    queryset = apps.get_model('band','Band').objects.filter(status=BandStatusChoices.ACTIVE).order_by('name')
    queryset = queryset.annotate(most_recent_gig=Max("gigs__created_date"))
    threshold = datetime.now(timezone('UTC')) - timedelta(days=30)
    queryset = queryset.filter(most_recent_gig__gt = threshold)
    return queryset

def _get_inactive_bands():
    """ return list of bands that haven't made a gig lately (or ever) """
    queryset = apps.get_model('band','Band').objects.filter(status=BandStatusChoices.ACTIVE).order_by('name')
    queryset = queryset.annotate(most_recent_gig=Max("gigs__created_date"))
    threshold = datetime.now(timezone('UTC')) - timedelta(days=30)
    queryset = queryset.filter( Q(most_recent_gig__lte = threshold) | Q(most_recent_gig = None))
    return queryset
