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

from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
import datetime
from dateutil.parser import parse
from django.db.models import Q

from gig.models import Gig
from band.models import Assoc
from member.util import AgendaChoices

import json
import logging


@login_required
def calendar_events(request, pk):
    startstr = request.GET['start']
    endstr = request.GET['end']

    start = parse(startstr)
    end = parse(endstr)

    user = request.user
    user_assocs = request.user.confirmed_assocs

    band_colors = { a.band.id:a.colorval for a in user_assocs }

    the_gigs = Gig.objects.filter(
        (Q(enddate__lte=end) | Q(enddate=None)),
        date__gte=start,
        band__in=[a.band for a in user_assocs],
    )

    events = []
    for g in the_gigs:
        gig = {}
        gig['title'] = g.title
        gig['start'] = str(g.date)
        if g.enddate:
            gig['end'] = str(g.enddate)
        gig['url'] = f'/gig/{g.id}'
        gig['backgroundColor'] = band_colors[g.band.id]
        if band_colors[g.band.id] == 'white':
            gig['borderColor'] = 'blue'
            gig['textColor'] = 'blue'
        else:
            gig['borderColor'] = band_colors[g.band.id]
        events.append(gig)

    return HttpResponse(json.dumps(events))


@login_required
def set_default_view(request, val):
    try:
        request.user.preferences.default_view=AgendaChoices(val)
    except ValueError:
        logging.error('user tried to set default view to something strange')
    request.user.preferences.save()
    return HttpResponseRedirect('/')
