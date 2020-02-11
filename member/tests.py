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

from unittest.mock import patch, mock_open

from django.test import TestCase, RequestFactory
from .models import Member, MemberPreferences
from band.models import Band, Assoc
from .views import AssocsView, OtherBandsView
from .helpers import prepare_email
from lib.email import DEFAULT_SUBJECT

class MemberTest(TestCase):
    def setUp(self):
        m=Member.objects.create_user('a@b.com', password='abc')
        b=Band.objects.create(name='test band')
        Assoc.objects.create(band=b, member=m)
        Band.objects.create(name='another band')

    def tearDown(self):
        """ make sure we get rid of anything we made """
        Member.objects.all().delete()
        Band.objects.all().delete()
        Assoc.objects.all().delete()

    def test_member_bands(self):
        """ test some basics of member creation """
        m = Member.objects.all()
        self.assertEqual(len(m), 1)
        m = m[0]
        self.assertEqual(len(m.assocs.all()),1)
        b = m.assocs.first().band
        self.assertEqual(b.name, 'test band')

    def test_memberassocsview(self):
        m = Member.objects.first()
        request = RequestFactory().get('/member/{}/assocs/'.format(m.id))
        view = AssocsView()
        view.setup(request, pk='{}'.format(m.id))

        context = view.get_context_data()
        self.assertIn('assocs', context)
        self.assertEqual(len(context['assocs']),1)
        self.assertEqual(context['assocs'][0].band.name, 'test band')

    def test_member_otherbandsview(self):
        m = Member.objects.first()
        request = RequestFactory().get('/member/{}/otherbands/'.format(m.id))
        view = OtherBandsView()
        view.setup(request, pk='{}'.format(m.id))

        context = view.get_context_data()
        self.assertIn('bands', context)
        self.assertEqual(len(context['bands']),1)
        self.assertEqual(context['bands'][0].name, 'another band')


class MemberEmailTest(TestCase):
    def setUp(self):
        self.member = Member.objects.create_user('member@example.com')

    def tearDown(self):
        Member.objects.all().delete()

    @patch('builtins.open', mock_open(read_data='**Markdown**'))
    def test_markdown_mail(self):
        message = prepare_email(self.member, 'template1')
        self.assertIn('**Markdown**', message.body)
        self.assertEqual(len(message.alternatives), 1)
        self.assertEqual(message.alternatives[0][1], 'text/html')
        self.assertIn('<strong>Markdown</strong>', message.alternatives[0][0])

    @patch('builtins.open', mock_open(read_data='{{ key }}'))
    def test_markdown_template(self):
        message = prepare_email(self.member, 'template2', {'key': 'value'})
        self.assertIn('value', message.body)
        self.assertIn('value', message.alternatives[0][0])

    @patch('builtins.open', mock_open(read_data='{{ member.email }}'))
    def test_markdown_template_member(self):
        message = prepare_email(self.member, 'template3')
        self.assertIn(self.member.email, message.body)
        self.assertIn(self.member.email, message.alternatives[0][0])

    @patch('builtins.open', mock_open(read_data='Body'))
    def test_markdown_default_subject(self):
        message = prepare_email(self.member, 'template4')
        self.assertEqual(message.subject, DEFAULT_SUBJECT)
        self.assertEqual(message.body, 'Body')

    @patch('builtins.open', mock_open(read_data='Subject: Custom\nBody'))
    def test_markdown_subject(self):
        message = prepare_email(self.member, 'template5')
        self.assertEqual(message.subject, 'Custom')
        self.assertEqual(message.body, 'Body')

    @patch('builtins.open', mock_open())
    def test_email_to_no_username(self):
        message = prepare_email(self.member, 'template6')
        self.assertEqual(message.to[0], 'member@example.com')

    @patch('builtins.open', mock_open())
    def test_email_to_username(self):
        self.member.username = 'Member Username'
        message = prepare_email(self.member, 'template7')
        self.assertEqual(message.to[0], 'Member Username <member@example.com>')
