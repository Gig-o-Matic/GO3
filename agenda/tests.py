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
from gig.tests import GigTestBase
from gig.util import GigStatusChoices, PlanStatusChoices
from gig.models import Plan
from member.util import AgendaLayoutChoices
from agenda.helpers import _get_agenda_plans
from band.models import Band, Assoc
from band.util import AssocStatusChoices
from django.test import Client
from django.urls import reverse
from json import loads
from datetime import datetime, timedelta, timezone as dttimezone
from django.utils import timezone
from freezegun import freeze_time

class AgendaTest(GigTestBase):
    def test_agenda_types(self):
        """ Test the different URLs for returning panels on the agenda page """
        self.assoc_user(self.joeuser)
        gigs = []
        for i in range(0, 19):
            gigs.append(self.create_gig_form(contact=self.joeuser, title=f"xyzzy{i}"))
        c = Client()
        c.force_login(self.joeuser)
        self.joeuser.preferences.agenda_layout = AgendaLayoutChoices.ONE_LIST
        self.joeuser.preferences.save()

        # get as a single list
        response = c.get(f'/plans/{int(AgendaLayoutChoices.ONE_LIST)}/0')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 19)

        # while we're here, check the plans count URL
        response = c.get(f'/schedule/planscount/0/0')
        self.assertEqual(response.content.decode('ascii'),"19")

        # test "has plans" vs. "doesn't have plans"

        first_gig = gigs[0]
        plan = first_gig.plans.get(assoc__member=self.joeuser)
        plan.status = PlanStatusChoices.DEFINITELY
        plan.save()

        response = c.get(f'/plans/{int(AgendaLayoutChoices.NEED_RESPONSE)}/0')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 18)

        # while we're here, check the need plans count URL
        response = c.get(f'/schedule/planscount/{int(AgendaLayoutChoices.NEED_RESPONSE)}/0')
        self.assertEqual(response.content.decode('ascii'),"18")

        # while we're here, check the needs response counter URL
        response = c.get(f'/schedule/planscount/{int(AgendaLayoutChoices.ONE_LIST)}/0')
        self.assertEqual(response.content.decode('ascii'),"19")

        # now make sure that a gig that is canceled is moved to the "plans" set even
        # though it has no plans...
        gigs[1].status = GigStatusChoices.CANCELED
        gigs[1].save()
        response = c.get(f'/plans/{int(AgendaLayoutChoices.NEED_RESPONSE)}/0')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 17)

        # while we're here, check the plans count URL
        response = c.get(f'/schedule/planscount/{int(AgendaLayoutChoices.ONE_LIST)}/0')
        self.assertEqual(response.content.decode('ascii'),"19")

        # Add another band
        b2 = Band.objects.create(
            name="test band 2",
            timezone="UTC",
            anyone_can_create_gigs=True,
        )
        
        Assoc.objects.create(member=self.joeuser, band=b2, status=AssocStatusChoices.CONFIRMED)
        self.create_gig_form(contact=self.joeuser, title=f"xyzzy{i}", band=b2)

        response = c.get(f'/schedule/planscount/{int(AgendaLayoutChoices.ONE_LIST)}/{self.band.id}')
        self.assertEqual(response.content.decode('ascii'),"20")

        # show that one band has 19 and the other has 1
        response = c.get(f'/schedule/planscount/{int(AgendaLayoutChoices.BY_BAND)}/{self.band.id}')
        self.assertEqual(response.content.decode('ascii'),"19")

        response = c.get(f'/schedule/planscount/{int(AgendaLayoutChoices.BY_BAND)}/{b2.id}')
        self.assertEqual(response.content.decode('ascii'),"1")

    def test_agenda_date_display(self):
        """ Test the different date displays on the agenda page """
        self.assoc_user(self.joeuser)
        g = self.create_gig_form(contact=self.joeuser, title=f"xyzzy")
        self.joeuser.preferences.current_timezone='America/New_York'
        self.joeuser.save()
        timezone.activate('America/New_York')
        g.date = timezone.make_aware(datetime(year=2028, month=4, day=1, hour=20))
        g.save()
        c = Client()
        c.force_login(self.joeuser)
        self.joeuser.preferences.agenda_layout = AgendaLayoutChoices.ONE_LIST
        self.joeuser.preferences.save()

        response = c.get(f'/plans/{int(AgendaLayoutChoices.ONE_LIST)}/0')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 1)
        self.assertEqual(response.content.decode('ascii').count("4/01"), 1)

        # now make it day before the gig
        with freeze_time(g.date - timedelta(days=1)):
            c.force_login(self.joeuser)
            response = c.get(f'/plans/{int(AgendaLayoutChoices.ONE_LIST)}/0')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 1)
        self.assertEqual(response.content.decode('ascii').count("Tomorrow"), 1)

        # now make it day of the gig
        with freeze_time(g.date - timedelta(hours=1)):
            c.force_login(self.joeuser)
            response = c.get(f'/plans/{int(AgendaLayoutChoices.ONE_LIST)}/0')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 1)
        self.assertEqual(response.content.decode('ascii').count("Today"), 1)

        # now do it again but move me to another timezone
        self.joeuser.preferences.current_timezone='UTC'
        self.joeuser.save()

        # now show that the agenda is different in different timezones
        # make gig on 4/1 6pm in New York - that's 10 or 11 UTC
        # make current time 4/1 12am UTC
        # in UTC, gig is "today", in New_York it's "tomorrow"

        g.date = timezone.make_aware(datetime(year=2028, month=4, day=1, hour=18))
        g.save()

        # now make it day before the gig UTC
        timezone.activate('UTC')
        the_time = timezone.make_aware(datetime(year=2028, month=4, day=1, hour=0))
        with freeze_time( the_time ):
            self.joeuser.preferences.current_timezone='UTC'
            self.joeuser.save()
            timezone.activate('UTC')
            c.force_login(self.joeuser)
            response = c.get(f'/plans/{int(AgendaLayoutChoices.ONE_LIST)}/0')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 1)
        self.assertEqual(response.content.decode('ascii').count("Today"), 1)

        with freeze_time( the_time ):
            self.joeuser.preferences.current_timezone='America/New_York'
            self.joeuser.save()
            c.force_login(self.joeuser)
            response = c.get(f'/plans/{int(AgendaLayoutChoices.ONE_LIST)}/0')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 1)
        self.assertEqual(response.content.decode('ascii').count("Tomorrow"), 1)

    def test_agenda_occasionals(self):
        _ = self.assoc_user(self.joeuser)
        janeassoc = self.assoc_user(self.janeuser)
        janeassoc.is_occasional = True
        janeassoc.save()

        gig1 = self.create_gig_form(contact=self.joeuser, title=f"xyzzy")
        gig1.invite_occasionals = False
        gig1.save()
        gig2 = self.create_gig_form(contact=self.joeuser, title=f"xyzzy")
        gig2.invite_occasionals = True
        gig2.save()

        joeplans = self.joeuser.future_noplans
        self.assertEqual(len(joeplans),2)

        janeplans = self.janeuser.future_noplans
        self.assertEqual(len(janeplans),1)

        gig1.invite_occasionals = True
        gig1.save()

        joeplans = self.joeuser.future_noplans
        self.assertEqual(len(joeplans),2)

        janeplans = self.janeuser.future_noplans
        self.assertEqual(len(janeplans),2)

    def test_hide_canceled_gigs(self):
        self.assoc_user(self.joeuser)
        self.joeuser.preferences.hide_canceled_gigs = True
        self.joeuser.preferences.save()

        self.create_one_gig_of_each_status()

        c = Client()
        c.force_login(self.joeuser)
        # first 'page' of gigs should not show the canceled gig
        response = c.get(f'/plans/noplans/1')
        self.assertEqual(response.content.decode('ascii').count("Canceled Gig-xyzzy"), 0)

    def test_hide_band_from_calendar_preference(self):
        a = self.assoc_user(self.joeuser)
        a.hide_from_schedule = False
        a.save()
        self.create_gig_form(contact=self.joeuser, title=f"xyzzy")

        c = Client()
        c.force_login(self.joeuser)
        # first 'page' of gigs should show the gig
        response = c.get(f'/plans/{int(AgendaLayoutChoices.NEED_RESPONSE)}/0')

        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 1)

        a.hide_from_schedule = True
        a.save()
        # first 'page' of gigs should not show the gig
        response = c.get(f'/plans/{int(AgendaLayoutChoices.NEED_RESPONSE)}/0')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 0)

    def test_agenda_page_types(self):
        """
        There are lots of different ways to have an agenda page. Tests them all!
        - Single list
        - Single list with hidden band
        - Split by 'needs plan'
        - ditto with hidden band
        - Split by band
        - ditto with hidden band
        """
        joe = self.joeuser
        b1 = self.band
        b1.anyone_can_create_gigs=True
        b1.save()
        a1 = Assoc.objects.create(member=joe, band=b1, status=AssocStatusChoices.CONFIRMED)

        b2 = Band.objects.create(
            name="test band 2",
            timezone="UTC",
            anyone_can_create_gigs=True,
        )
        a2 = Assoc.objects.create(member=joe, band=b2, status=AssocStatusChoices.CONFIRMED)

        gigs = []
        gigs.append(self.create_gig_form(user=joe, contact=joe, title='test1', call_date="01/03/2100", band=b1))
        gigs.append(self.create_gig_form(user=joe, contact=joe, title='test2', call_date="01/04/2100", band=b1))
        gigs.append(self.create_gig_form(user=joe, contact=joe, title='test3', call_date="01/05/2100", band=b1))
        gigs.append(self.create_gig_form(user=joe, contact=joe, title='test1b', call_date="01/03/2100", band=b2))
        gigs.append(self.create_gig_form(user=joe, contact=joe, title='test2b', call_date="01/04/2100", band=b2))
        gigs.append(self.create_gig_form(user=joe, contact=joe, title='test3b', call_date="01/05/2100", band=b2))

        joe.preferences.agenda_layout = AgendaLayoutChoices.ONE_LIST
        joe.preferences.save()

        # test single list with all bands
        a2.hide_from_schedule = False
        a2.save()
        the_list, _ = _get_agenda_plans(joe, AgendaLayoutChoices.ONE_LIST, 0)
        self.assertEqual(len(the_list), 6)

        # test single list with a hidden band
        a2.hide_from_schedule = True
        a2.save()
        the_list, _ = _get_agenda_plans(joe, AgendaLayoutChoices.ONE_LIST, 0)
        self.assertEqual(len(the_list), 3)

        a2.hide_from_schedule = False
        a2.save()

        # test Split by 'needs plan'

        # register a plan
        p = Plan.objects.get(gig=gigs[0], assoc=a1)
        p.status = PlanStatusChoices.DEFINITELY
        p.save()

        the_list, _ = _get_agenda_plans(joe, AgendaLayoutChoices.NEED_RESPONSE, 0)
        self.assertEqual(len(the_list), 5)

        # test ditto with hidden band
        a2.hide_from_schedule = True
        a2.save()

        the_list, _ = _get_agenda_plans(joe, AgendaLayoutChoices.NEED_RESPONSE, 0)
        self.assertEqual(len(the_list), 2)

        a1.hide_from_schedule = True
        a1.save()

        the_list, _ = _get_agenda_plans(joe, AgendaLayoutChoices.NEED_RESPONSE, 0)
        self.assertEqual(len(the_list), 0)

        a1.hide_from_schedule = False
        a1.save()
        a2.hide_from_schedule = False
        a2.save()

        # test split by band
        the_list, _ = _get_agenda_plans(joe, AgendaLayoutChoices.BY_BAND, b1.id)
        self.assertEqual(len(the_list), 3)

        the_list, _ = _get_agenda_plans(joe, AgendaLayoutChoices.BY_BAND, b2.id)
        self.assertEqual(len(the_list), 3)

        # test ditto with hidden band
        a2.hide_from_schedule = True
        a2.save()

        the_list, _ = _get_agenda_plans(joe, AgendaLayoutChoices.BY_BAND, b1.id)
        self.assertEqual(len(the_list), 3)

        the_list, _ = _get_agenda_plans(joe, AgendaLayoutChoices.BY_BAND, b2.id)
        self.assertEqual(len(the_list), 0)



class CalendarTest(GigTestBase):
    def test_calendar(self):
        self.assoc_user(self.joeuser)
        self.create_one_gig_of_each_status()

        self.joeuser.preferences.hide_canceled_gigs = False
        self.joeuser.preferences.calendar_show_only_confirmed = False
        self.joeuser.preferences.calendar_show_only_committed = False
        self.joeuser.preferences.save()

        c = Client()
        c.force_login(self.joeuser)

        startdate = datetime(2099, 12, 1, 0, 0, 0, 0, dttimezone.utc)
        enddate = datetime(2100, 2, 1, 0, 0, 0, 0, dttimezone.utc)
        response = c.get(reverse('calendar-events', args=[self.band.id]), data={
            'start': startdate.isoformat(),
            'end': enddate.isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        data = loads(response.content)
        self.assertEqual(len(data), 4)

    def test_hide_canceled_gigs(self):
        self.assoc_user(self.joeuser)
        self.joeuser.preferences.hide_canceled_gigs = True
        self.joeuser.preferences.calendar_show_only_confirmed = False
        self.joeuser.preferences.calendar_show_only_committed = False
        self.joeuser.preferences.save()

        self.create_one_gig_of_each_status()

        c = Client()
        c.force_login(self.joeuser)
        startdate = datetime(2099, 12, 1, 0, 0, 0, 0, dttimezone.utc)
        enddate = datetime(2100, 2, 1, 0, 0, 0, 0, dttimezone.utc)
        response = c.get(reverse('calendar-events', args=[self.band.id]), data={
            'start': startdate.isoformat(),
            'end': enddate.isoformat(),
        })

        self.assertEqual(response.status_code, 200)
        data = loads(response.content)
        self.assertEqual(len(data), 3)

    def test_show_only_confirmed(self):
        self.assoc_user(self.joeuser)
        self.joeuser.preferences.hide_canceled_gigs = False
        self.joeuser.preferences.calendar_show_only_confirmed = True
        self.joeuser.preferences.calendar_show_only_committed = False
        self.joeuser.preferences.save()

        self.create_one_gig_of_each_status()

        c = Client()
        c.force_login(self.joeuser)
        startdate = datetime(2099, 12, 1, 0, 0, 0, 0, dttimezone.utc)
        enddate = datetime(2100, 2, 1, 0, 0, 0, 0, dttimezone.utc)
        response = c.get(reverse('calendar-events', args=[self.band.id]), data={
            'start': startdate.isoformat(),
            'end': enddate.isoformat(),
        })

        self.assertEqual(response.status_code, 200)
        data = loads(response.content)
        self.assertEqual(len(data), 1)

class GridTest(GigTestBase):
    def test_grid(self):
        self.assoc_user(self.joeuser)
        for i in range(0, 19):
            self.create_gig_form(contact=self.joeuser, title=f"xyzzy{i}")
        c = Client()
        c.force_login(self.joeuser)

        # see that the band has users
        response = c.post(reverse('grid-section-members'),
                          data={'band': self.band.id})
        self.assertEqual(response.status_code, 200)
        data = loads(response.content)
        self.assertEqual(len(data), 1)
        band = data[0]
        self.assertTrue(type(band) == dict)
        self.assertTrue('members' in band.keys())
        self.assertTrue(len(band['members']) == 2)

        # see the right number of gigs
        response = c.post(reverse('grid-gigs'), data={
            'band': self.band.id,
            'month': 0,  # need this to be month-1 because that's how it works in the javascript
            'year': 2100,
        })
        self.assertEqual(response.status_code, 200)
        gigs = loads(response.content)
        self.assertEqual(len(gigs), 19)

    def test_hide_canceled_gigs(self):
        self.assoc_user(self.joeuser)
        self.joeuser.preferences.hide_canceled_gigs = True
        self.joeuser.preferences.calendar_show_only_confirmed = False
        self.joeuser.preferences.calendar_show_only_committed = False
        self.joeuser.preferences.save()

        self.create_one_gig_of_each_status()

        c = Client()
        c.force_login(self.joeuser)

        # see the right number of gigs
        response = c.post(reverse('grid-gigs'), data={
            'band': self.band.id,
            'month': 0,  # need this to be month-1 because that's how it works in the javascript
            'year': 2100,
        })
        self.assertEqual(response.status_code, 200)
        gigs = loads(response.content)
        self.assertEqual(len(gigs), 3)
