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
from gig.tests import GigTestBase

class StatsTest(GigTestBase):

    def test_band_member_stat(self):
        """ show that we collect band member stats properly """
        self.assoc_joe()
        collect_band_stats()

        m = BandMetric.objects.get(name='Number of Members', band=self.band)
        self.assertEqual(m.stats.count(),1)
        self.assertEqual(m.stats.first().value,self.band.confirmed_assocs.count())

    def test_band_member_stat_delete(self):
        """ show that we collect band member stats properly after member is deleted """
        self.assoc_joe()
        self.joeuser.delete()

        collect_band_stats()

        m = BandMetric.objects.get(name='Number of Members', band=self.band)
        self.assertEqual(m.stats.count(),1)
        self.assertEqual(self.band.confirmed_assocs.count(),1)
        self.assertEqual(m.stats.first().value,self.band.confirmed_assocs.count())

    def test_band_gigcount_stat(self):
        """ show that we collect band gig count stats properly """
        self.assoc_joe_and_create_gig()
        self.create_gig_form(contact=self.joeuser)
        collect_band_stats()
        m = BandMetric.objects.get(name='Number of Gigs', band=self.band)
        self.assertEqual(m.stats.count(),1)
        self.assertEqual(m.stats.first().value,2)

