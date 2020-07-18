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
from django.test import Client

class AgendaTest(GigTestBase):
    def test_agenda(self):
        self.assoc_joe()
        for i in range(0,19):
            self.create_gig_form(contact=self.joeuser, title=f"xyzzy{i}")
        c=Client()
        c.force_login(self.joeuser)

        # first 'page' of gigs should have 10
        response = c.get(f'/plans/noplans/1')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"),10)

        # second 'page' of gigs should have 9
        response = c.get(f'/plans/noplans/2')
        self.assertEqual(response.content.decode('ascii').count("xyzzy"),9)



