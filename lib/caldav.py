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
from django.core.files.storage import default_storage, FileSystemStorage
from icalendar import Calendar, Event
from datetime import timedelta, datetime
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _
from gig.util import GigStatusChoices
from django.conf import settings
from go3.settings import URL_BASE

if default_storage.__class__ == FileSystemStorage:
    default_storage.location = f'{settings.CALFEED_BASEDIR}calfeeds'
    default_storage.base_url = 'calfeeds'


def save_calfeed(tag, content):
    file_path = f'{tag}.txt'

    with default_storage.open(file_path, mode='wb') as f:
        f.write(content)


def get_calfeed(tag):
    try:
        with default_storage.open('{0}.txt'.format(tag), mode='r') as f:
            s = f.read()
    except FileNotFoundError:
        raise ValueError()
    return s


def delete_calfeed(tag):
    if settings.DYNAMIC_CALFEED is False:
        file_path = f'{tag}.txt'
        if default_storage.exists(file_path):
            default_storage.delete(file_path)


def _make_calfeed_metadata(the_source):
    cal = Calendar()
    cal.add('prodid', '-//Gig-o-Matic//gig-o-matic.com//')
    cal.add('version', '3.0')
    cal.add('X-WR-CALNAME', the_source)
    cal.add('X-WR-CALDESC',
            '{0} {1}'.format(_('Gig-o-Matic calendar for'), the_source))
    return cal


def _make_calfeed_event(gig, is_for_band):
    def _make_description(gig):
        """ description is the details, plus the setlist """
        if is_for_band:
            deets = gig.public_description or ''
        else:
            deets = gig.details or ''
        setlist = gig.setlist or ''
        space = '\n\n' if deets and setlist else ''
        return f'{deets}{space}{setlist}'

    event = Event()
    event.add('dtstamp', timezone.now())
    event.add('uid', gig.cal_feed_id)
    summary = f'{gig.title} ({GigStatusChoices(gig.status).label}) - {gig.band.name}'
    event.add('summary', summary)
    if gig.is_full_day:
        date = gig.date.date()
        startdate = datetime.combine(date, datetime.min.time())
        event.add('dtstart', startdate, {'value': 'DATE'})
        # To make the event use the full final day, icalendar clients expect the end date
        # to be the date after the event ends. So we add 1 day.
        # https://datatracker.ietf.org/doc/html/rfc5545#section-3.6.1:
        # "The "DTEND" property for a "VEVENT" calendar component specifies
        # the non-inclusive end of the event."
        enddate = (gig.enddate if gig.enddate else gig.date).date() + timedelta(days=1)
        enddate = datetime.combine(enddate, datetime.min.time())
        event.add('dtend', enddate, {'value': 'DATE'})
    else:
        setdate = gig.setdate if (is_for_band and gig.setdate) else gig.date
        event.add('dtstart', setdate)
        enddate = gig.enddate if gig.enddate else gig.date + timedelta(hours=1)
        event.add('dtend', enddate)
    event.add('description', _make_description(gig))
    event.add('location', gig.address)
    event.add('url', f'{URL_BASE}/gig/{gig.id}')
    # todo don't hardwire the URL
    # todo go2 also has sequence:0, status:confirmed, and transp:opaque attributes - need those?
    return event


def make_member_calfeed(member, the_plans):
    """ construct an ical-compliant stream from a list of plans """

    # member.cal_feed_id # TODO uid

    with translation.override(member.preferences.language):
        cal = _make_calfeed_metadata(member)
        for plan in the_plans:
            event = _make_calfeed_event(plan.gig, is_for_band=False)
            cal.add_component(event)
    return cal.to_ical()


def make_band_calfeed(band, the_gigs):
    """ construct an ical-compliant stream from a list of gigs """
    # band.pub_cal_feed_id  TODO use uid?

    with translation.override(band.default_language):
        cal = _make_calfeed_metadata(band)
        for gig in the_gigs:
            event = _make_calfeed_event(gig, is_for_band=True)
            cal.add_component(event)
    return cal.to_ical()
