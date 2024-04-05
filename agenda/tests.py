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
from django.test import Client
from django.urls import reverse
from json import loads
from datetime import datetime
from pytz import timezone

class AgendaTest(GigTestBase):
    def test_agenda(self):
        self.assoc_user(self.joeuser)
        gigs = []
        for i in range(0, 19):
            gigs.append(self.create_gig_form(contact=self.joeuser, title=f"xyzzy{i}"))
        c = Client()
        c.force_login(self.joeuser)

        # first 'page' of gigs should have 19 (because pagination is very long)
        response = c.get(f'/plans/noplans/1')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 19)

        first_gig = gigs[0]
        plan = first_gig.plans.get(assoc__member=self.joeuser)
        plan.status = PlanStatusChoices.DEFINITELY
        plan.save()
        response = c.get(f'/plans/noplans/1')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 18)
        response = c.get(f'/plans/plans/1')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 1)

        # now make sure that a gig that is canceled is moved to the "plans" set even
        # though it has no plans...
        gigs[1].status = GigStatusChoices.CANCELED
        gigs[1].save()
        response = c.get(f'/plans/noplans/1')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 17)
        response = c.get(f'/plans/plans/1')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 2)


        # tests that pass if pagination is set to 10        
        # # first 'page' of gigs should have 10
        # response = c.get(f'/plans/noplans/1')
        # self.assertEqual(response.content.decode('ascii').count("xyzzy"), 10)

        # # second 'page' of gigs should have 9
        # response = c.get(f'/plans/noplans/2')
        # self.assertEqual(response.content.decode('ascii').count("xyzzy"), 9)

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
        response = c.get(f'/plans/noplans/1')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 1)

        a.hide_from_schedule = True
        a.save()
        # first 'page' of gigs should not show the gig
        response = c.get(f'/plans/noplans/1')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"), 0)


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

        startdate = datetime(2099, 12, 1, 0, 0, 0, 0, timezone('UTC'))
        enddate = datetime(2100, 2, 1, 0, 0, 0, 0, timezone('UTC'))
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
        startdate = datetime(2099, 12, 1, 0, 0, 0, 0, timezone('UTC'))
        enddate = datetime(2100, 2, 1, 0, 0, 0, 0, timezone('UTC'))
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
        startdate = datetime(2099, 12, 1, 0, 0, 0, 0, timezone('UTC'))
        enddate = datetime(2100, 2, 1, 0, 0, 0, 0, timezone('UTC'))
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
