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

from django.test import TestCase, RequestFactory
from member.models import Member
from .settings import LANGUAGES
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.urls import reverse


class LanguageTest(TestCase):
    def test_language(self):
        translation.activate("en-us")
        self.assertEqual(_("Schedule"), "Schedule")
        translation.activate("fr")
        self.assertEqual(_("Schedule"), "Liste des concerts ")


class ErrorTest(TestCase):
    def setUp(self):
        self.member = Member.objects.create_user("a@b.com", password="abc")

    def test_404(self):
        self.client.force_login(self.member)
        response = self.client.get("/404")
        self.assertEqual(response.status_code, 404)
