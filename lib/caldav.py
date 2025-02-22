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
import os
from gig.util import GigStatusChoices
from django.conf import settings
from go3.settings import URL_BASE, BASE_DIR
import pytz

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


def make_calfeed(the_source, the_events, the_language, the_uid, is_for_band=False):
    """ construct an ical-compliant stream from a list of events """

    def _make_summary(event):
        """ makes the summary: the title, plus band name and status """
        return f'{event.title} ({GigStatusChoices(event.status).label}) - {event.band.name}'

    def _make_description(event):
        """ description is the details, plus the setlist """
        deets = event.details if event.details else ''
        setlist = event.setlist if event.setlist else ''
        space = '\n\n' if deets and setlist else ''
        return f'{deets}{space}{setlist}'

    # set up language
    cal = Calendar()
    
    # figure out what the timezone should be
    try:
        tz = the_source.timezone
    except:
        return #  todo we shouldn't just fail silently
    zone = pytz.timezone(tz)

    with translation.override(the_language):
        cal.add('prodid', '-//Gig-o-Matic//gig-o-matic.com//')
        cal.add('version', '2.0')
        cal.add('X-WR-CALNAME', the_source)
        cal.add('X-WR-CALDESC',
                '{0} {1}'.format(_('Gig-o-Matic calendar for'), the_source))
        for e in the_events:
            event = Event()
            event.add('dtstamp', timezone.now())
            event.add('uid', e.cal_feed_id)
            event.add('summary', _make_summary(e))
            if e.is_full_day:
                date = e.date.date()
                startdate = datetime.combine(date,datetime.min.time())
                startdate = startdate.replace(tzinfo = zone)
                event.add('dtstart', startdate, {'value': 'DATE'})
                # To make the event use the full final day, icalendar clients expect the end date
                # to be the date after the event ends. So we add 1 day.
                # https://datatracker.ietf.org/doc/html/rfc5545#section-3.6.1:
                # "The "DTEND" property for a "VEVENT" calendar component specifies
                # the non-inclusive end of the event."
                enddate = (e.enddate if e.enddate else e.date).date() + timedelta(days=1)
                enddate = datetime.combine(enddate,datetime.min.time())
                enddate = enddate.replace(tzinfo = zone)
                event.add('dtend', enddate, {'value': 'DATE'})
            else:
                setdate = e.setdate if (is_for_band and e.setdate) else e.date
                setdate = setdate.replace(tzinfo=zone)
                event.add('dtstart', setdate)
                enddate = e.enddate if e.enddate else e.date + timedelta(hours=1)
                enddate = enddate.replace(tzinfo=zone)
                event.add('dtend', enddate)
            event.add('description', _make_description(e))
            event.add('location', e.address)
            event.add(
                'url', f'{URL_BASE}/gig/{e.id}')
            # todo don't hardwire the URL
            # todo go2 also has sequence:0, status:confirmed, and transp:opaque attributes - need those?
            cal.add_component(event)
    return cal.to_ical()
