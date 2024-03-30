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
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
import datetime
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from pytz import timezone as pytz_timezone
from datetime import timedelta

from django.db.models import Q

from gig.models import Gig, Plan, GigStatusChoices
from band.models import Band, Assoc, Section
from band.util import AssocStatusChoices
from member.util import AgendaChoices

import json
import logging

from go3.colors import the_colors
from django.shortcuts import render
from django.core.paginator import Paginator

# This controls the pagination of gigs on the agenda page. There was strong pushback against the paging
# mechanism, so this basically defeats it. But I still think the paginator is a good idea, and it may be worth
# putting it back in as an option. For now, though, instead of ripping it out, it's disabled.
PAGE_LENGTH = 10000


@login_required
def agenda_gigs(request, the_type=None, page=1):

    if the_type == 'noplans':
        the_plans = request.user.future_noplans.all()
    else:
        the_plans = request.user.future_plans.all()

    paginator = Paginator(the_plans, PAGE_LENGTH)
    page_obj = paginator.get_page(page)

    return render(request, 'agenda/agenda_gigs.html', {'the_colors:': the_colors, 'page_obj': page_obj, 'the_type': the_type})


@login_required
def calendar_events(request, pk):
    startstr = request.GET['start']
    endstr = request.GET['end']

    start = parse(startstr)
    end = parse(endstr)

    user_assocs = request.user.confirmed_assocs
    hide_canceled_gigs = request.user.preferences.hide_canceled_gigs
    show_only_confirmed = request.user.preferences.calendar_show_only_confirmed

    band_colors = {a.band.id: a.colorval for a in user_assocs}

    plans = request.user.calendar_plans

    plans = plans.filter(
        (Q(gig__enddate__lte=end) | Q(gig__enddate=None)),
        gig__date__gte=start,
    )
    if hide_canceled_gigs:
        plans = plans.exclude(gig__status=GigStatusChoices.CANCELED)
    if show_only_confirmed:
        plans = plans.filter(gig__status=GigStatusChoices.CONFIRMED)

    the_gigs = [p.gig for p in plans]

    events = []
    multiband = len(user_assocs) > 1
    for g in the_gigs:
        gig = {}
        gig['title'] = f'{g.band.shortname or g.band.name}: {g.title}' if multiband else g.title

        enddate = g.enddate if g.enddate else g.date
        if g.is_full_day:
            gig['start'] = str(g.date.date())
            # Like icalendar, the end date is expected to be non-inclusive
            gig['end'] = str(enddate.date() + timedelta(days=1))
            gig['allDay'] = True
        else:
            gig['start'] = str(g.date)
            gig['end'] = str(g.enddate)

        gig['url'] = f'/gig/{g.id}'

        # Gig styling
        gig['display'] = 'block'
        gig['backgroundColor'] = band_colors[g.band.id]
        if band_colors[g.band.id] == 'white' or band_colors[g.band.id] == '#ffffff':
            gig['textColor'] = '#000'
        else:
            gig['textColor'] = '#fff'

        events.append(gig)

    return HttpResponse(json.dumps(events))


@login_required
def set_default_view(request, val):
    try:
        request.user.preferences.default_view = AgendaChoices(val)
    except ValueError:
        logging.error('user tried to set default view to something strange')
    request.user.preferences.save()
    return HttpResponse()


@login_required
def grid_heatmap(request, *args, **kw):
    year = int(request.POST['year'])
    band_id = int(request.POST['band'])

    the_gigs = Gig.objects.filter(
        date__year=year,
        band=band_id,
        trashed_date__isnull=True,
        ).order_by('date').values('date')

    uncooked_data = {}
    for g in the_gigs:
        m = g['date'].month
        d = g['date'].day
        cooked_date = f"{year}-{m:02}-{d:02}"
        if cooked_date in uncooked_data:
            uncooked_data[cooked_date] += 1
        else:
            uncooked_data[cooked_date] = 1

    data = []
    for d in uncooked_data.keys():
        data.append({
            'count': uncooked_data[d],
            'date': d
        })

    return HttpResponse(json.dumps(data))


@login_required
def grid_section_members(request, *args, **kw):
    band_id = int(request.POST['band'])
    assocs = Assoc.objects.filter(
        band=band_id, status=AssocStatusChoices.CONFIRMED).order_by('default_section__order')
    mbs = {}
    for a in assocs:
        info = {'id': a.member.id, 'name': a.member.display_name}
        if a.default_section.id in mbs.keys():
            mbs[a.default_section.id]['members'].append(info)
        else:
            mbs[a.default_section.id] = {
                'name': a.default_section.name, 'members': [info]}

    # convert to just a list
    data = [{"id": x, "name": mbs[x]['name'], "members":mbs[x]['members']}
            for x in mbs]
    return HttpResponse(json.dumps(data))


@login_required
def grid_gigs(request, *args, **kw):
    band_id = int(request.POST['band'])
    month = int(request.POST['month'])
    year = int(request.POST['year'])

    # can't just filter by date__month because that doesn't seem to work in mariadb
    band = Band.objects.get(id=band_id)
    start = datetime.datetime(year=year, month=month+1, day=1, tzinfo=pytz_timezone(band.timezone))
    end = start + relativedelta(months=1)
    gigs = Gig.objects.filter(
        date__gte=start,
        date__lt=end,
        band=band_id,
        trashed_date__isnull=True,
        hide_from_calendar=False,
        ).order_by('date')
    if request.user.preferences.hide_canceled_gigs:
        gigs = gigs.exclude(status=GigStatusChoices.CANCELED)

    data = []
    for g in gigs:
        all_plans = Plan.objects.filter(gig=g).select_related()
        member_plans = [{'member': p.assoc.member_id,
                         'plan': p.status} for p in all_plans]
        data.append({
            'title': g.title,
            'date': str(g.date),
            'id': g.id,
            'plans': member_plans
        })
    return HttpResponse(json.dumps(data))
