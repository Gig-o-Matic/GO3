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
from django.urls import get_resolver, reverse
from django.utils import translation
from django.utils.translation import gettext_lazy as _

from member.models import Member


class LanguageTest(TestCase):
    def test_language(self):
        translation.activate("en-us")
        self.assertEqual(_("Schedule"), "Schedule")
        translation.activate("fr")
        self.assertEqual(_("Schedule"), "Liste des concerts")

class ErrorTest(TestCase):
    def setUp(self):
        self.member = Member.objects.create_user('a@b.com', password='abc')

    def test_404(self):
        self.client.force_login(self.member)
        response = self.client.get('/404')
        self.assertEqual(response.status_code, 404)


class TestGO3API(TestCase):
    def setUp(self):
        self.member = Member.objects.create_user('a@b.com', password='abc', api_key="test")

    def test_missing_api_key(self):
        response = self.client.get(reverse("api-1.0.0:whoami"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"message": "Missing API key"})

    def test_invalid_api_key(self):
        response = self.client.get(reverse("api-1.0.0:whoami"), HTTP_X_API_KEY="abc")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"message": "Invalid API key"})

    def test_valid_api_key(self):
        response = self.client.get(reverse("api-1.0.0:whoami"), HTTP_X_API_KEY=self.member.api_key)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"key": self.member.api_key})


class TestAllURLs(TestCase):
    def setUp(self):
        # TODO: generate some objects to use in the url test
        return super().setUp()
    
    def test_urls(self):
        urls = set(v[1] for k,v in get_resolver(None).reverse_dict.items())
        for url in urls:
            # TODO: supply correct parameters to the request
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)
            self.assertNotEqual(response.content, b'')
