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
from django.test import TestCase
from .models import Metric, Stat, BandMetric
from .tasks import collect_band_stats
from member.models import Member
from band.models import Band, Assoc
from gig.tests import GigTestBase
from band.util import AssocStatusChoices
from freezegun import freeze_time
from datetime import datetime, timedelta
from django.utils import timezone

class StatsTest(GigTestBase):

    def add_members(self,num,band=None):
        c = Member.objects.count()
        members = []
        assocs = []
        if band is None:
            band = self.band
        for i in range(c,num+c):
            m = Member.objects.create_user(email=f'member{i}@b.c')
            members.append(m)
            a = Assoc.objects.create(member=m, band=self.band, status=AssocStatusChoices.CONFIRMED)
            assocs.append(a)
        return members, assocs

    def test_band_member_stat(self):
        """ show that we collect band member stats properly """
        Member.objects.all().delete()  # start from scratch
        self.add_members(1)
        self.assertEqual(self.band.confirmed_assocs.count(),1)
        collect_band_stats()
        m = BandMetric.objects.get(name='Number of Active Members', band=self.band)
        self.assertEqual(m.stats.count(),1)
        self.assertEqual(m.stats.first().value,self.band.confirmed_assocs.count())

        self.add_members(10)
        self.assertEqual(self.band.confirmed_assocs.count(),11)
        collect_band_stats()
        m = BandMetric.objects.get(name='Number of Active Members', band=self.band)
        self.assertEqual(m.stats.count(),1)  # this one is daily so if it's the same day, we still only have one
        self.assertEqual(m.stats.first().value,self.band.confirmed_assocs.count())


    def test_band_member_stat_daily(self):
        Member.objects.all().delete()  # start from scratch
        self.add_members(10)
        self.assertEqual(self.band.confirmed_assocs.count(),10)
        collect_band_stats()
        m = BandMetric.objects.get(name='Number of Active Members', band=self.band)
        self.assertEqual(m.stats.count(),1)
        self.assertEqual(m.stats.first().value,10)

        m = BandMetric.objects.get(name='All Time Number of Members', band=self.band)
        self.assertEqual(m.stats.count(),1)
        self.assertEqual(m.stats.first().value,10)

        self.add_members(1)
        # add a new one for the next day
        with freeze_time(timezone.now() + timedelta(days=1)):
            collect_band_stats()

        m = BandMetric.objects.get(name='Number of Active Members', band=self.band)
        self.assertEqual(m.stats.count(),2)
        self.assertEqual(m.stats.last().value,11)

        m = BandMetric.objects.get(name='All Time Number of Members', band=self.band)
        self.assertEqual(m.stats.count(),1)
        self.assertEqual(m.stats.first().value,11)


    def test_band_member_stat_delete(self):
        """ show that we collect band member stats properly after member is deleted """
        Member.objects.all().delete()  # start from scratch
        members, _ = self.add_members(10)
        collect_band_stats()

        m = BandMetric.objects.get(name='Number of Active Members', band=self.band)
        self.assertEqual(m.stats.count(),1)
        self.assertEqual(self.band.confirmed_assocs.count(),10)
        self.assertEqual(m.stats.first().value,10)

        members[0].delete()

        collect_band_stats() # same day so it'll delete the old metric

        m = BandMetric.objects.get(name='Number of Active Members', band=self.band)
        self.assertEqual(m.stats.count(),1)
        self.assertEqual(self.band.confirmed_assocs.count(),9)
        self.assertEqual(m.stats.first().value,9)

    def test_band_gigcount_stat(self):
        """ show that we collect band gig count stats properly """
        self.assoc_joe_and_create_gig()
        self.create_gig_form(contact=self.joeuser)
        collect_band_stats()
        m = BandMetric.objects.get(name='Number of Gigs', band=self.band)
        self.assertEqual(m.stats.count(),1)
        self.assertEqual(m.stats.first().value,2)

    def test_band_multiple_stat(self):
        """ show that every time we collect stats we...get more stats """
        self.assoc_joe_and_create_gig()
        collect_band_stats()
        m = BandMetric.objects.get(name='Number of Gigs', band=self.band)
        self.assertEqual(m.stats.count(),1)

        self.create_gig_form(contact=self.joeuser, call_date="01/03/2100")
        with freeze_time(timezone.now() + timedelta(days=1)): # count again tomorrow
            collect_band_stats()
        m = BandMetric.objects.get(name='Number of Gigs', band=self.band)
        self.assertEqual(m.stats.count(),2)  # should now be two
        self.assertEqual(m.stats.order_by('created').last().value,2)

    def test_all_time_members(self):
        Member.objects.all().delete()  # start from scratch
        _, assocs = self.add_members(10)
        assocs[0].status = AssocStatusChoices.NOT_CONFIRMED
        assocs[0].save()
        collect_band_stats()
        m = BandMetric.objects.get(name='Number of Active Members', band=self.band)
        self.assertEqual(m.stats.count(),1)
        self.assertEqual(m.stats.first().value, 9)

        m = BandMetric.objects.get(name='All Time Number of Members', band=self.band)
        self.assertEqual(m.stats.count(),1)
        self.assertEqual(m.stats.first().value, 10)

        # check the aggregate version
        b2 = Band.objects.create(
            name="test band 2",
            timezone="UTC",
        )

        # add a bunch of unassociated members
        self.add_members(10, b2)

        collect_band_stats()

        m = BandMetric.objects.get(name='Number of Active Members', band=None)
        self.assertEqual(m.stats.count(),1)
        self.assertEqual(m.stats.first().value, 19)
    
        m = BandMetric.objects.get(name='All Time Number of Members', band=None)
        self.assertEqual(m.stats.count(),1)
        self.assertEqual(m.stats.first().value, 20)
