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
from gig.models import Gig
from .views import AssocsView, OtherBandsView
from .helpers import prepare_email, prepare_calfeed
from lib.email import DEFAULT_SUBJECT

from django.utils import timezone
from datetime import timedelta
import pytz

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

        _open = open  # Saves a reference to the builtin, for access after patching
        def template_open(filename, *args, **kw):
            # We adopt the convention that a filename begining with 't:' indicates
            # a template that we want to inject, with the contents of the filename
            # following the 't:'.  But the template mechanism tries to open
            # absolute paths, so we need to look for 't:' anywhere in the filename.
            if isinstance(filename, str) and (i := filename.find('t:')) > -1:
                content = filename[i+2:]
                return mock_open(read_data=content).return_value
            return _open(filename, *args, **kw)

        self.patcher = patch('builtins.open', template_open)
        self.patcher.start()

    def tearDown(self):
        Member.objects.all().delete()
        self.patcher.stop()

    def test_markdown_mail(self):
        message = prepare_email(self.member, 't:**Markdown**')
        self.assertIn('**Markdown**', message.body)
        self.assertEqual(len(message.alternatives), 1)
        self.assertEqual(message.alternatives[0][1], 'text/html')
        self.assertIn('<strong>Markdown</strong>', message.alternatives[0][0])

    def test_markdown_template(self):
        message = prepare_email(self.member, 't:{{ key }}', {'key': 'value'})
        self.assertIn('value', message.body)
        self.assertIn('value', message.alternatives[0][0])

    def test_markdown_template_member(self):
        message = prepare_email(self.member, 't:{{ member.email }}')
        self.assertIn(self.member.email, message.body)
        self.assertIn(self.member.email, message.alternatives[0][0])

    def test_markdown_default_subject(self):
        message = prepare_email(self.member, 't:Body')
        self.assertEqual(message.subject, DEFAULT_SUBJECT)
        self.assertEqual(message.body, 'Body')

    def test_markdown_subject(self):
        message = prepare_email(self.member, 't:Subject: Custom\nBody')
        self.assertEqual(message.subject, 'Custom')
        self.assertEqual(message.body, 'Body')

    def test_markdown_html_escape(self):
        message = prepare_email(self.member, 't:1 < 2')
        self.assertIn('<', message.body)
        self.assertIn('&lt;', message.alternatives[0][0])

    def test_email_to_no_username(self):
        message = prepare_email(self.member, 't:')
        self.assertEqual(message.to[0], 'member@example.com')

    def test_email_to_username(self):
        self.member.username = 'Member Username'
        message = prepare_email(self.member, 't:')
        self.assertEqual(message.to[0], 'Member Username <member@example.com>')

    def test_translation_en(self):
        message = prepare_email(self.member, 't:{% load i18n %}{% blocktrans %}Translated text{% endblocktrans %}')
        self.assertEqual(message.body, 'Translated text')

    def test_translation_de(self):
        self.member.preferences.language = 'de'
        # This translation is already provided by Django
        message = prepare_email(self.member, 't:{% load i18n %}{% blocktrans %}German{% endblocktrans %}')
        self.assertEqual(message.body, 'Deutsch')

    def test_translation_before_subject(self):
        message = prepare_email(self.member, 't:{% load i18n %}\nSubject: {% blocktrans %}Subject Line{% endblocktrans %}\n\n{% blocktrans %}Body{% endblocktrans %}')
        self.assertEqual(message.subject, "Subject Line")
        self.assertEqual(message.body, "Body")

    def test_markdown_new_lines(self):
        message = prepare_email(self.member, 't:Line one\nLine two')
        self.assertIn('\n', message.body)
        # We want a new line, but it could show up as "<br>" or "<br />"
        self.assertIn('<br', message.alternatives[0][0])

class MemberCalfeedTest(TestCase):
    def setUp(self):
        """ fake a file system """
        self.super = Member.objects.create_user(email='a@b.c', is_superuser=True)
        self.band_admin = Member.objects.create_user(email='d@e.f')
        self.joeuser = Member.objects.create_user(email='g@h.i')
        self.janeuser = Member.objects.create_user(email='j@k.l')
        self.band = Band.objects.create(name='test band')
        Assoc.objects.create(member=self.joeuser, band=self.band, is_admin=True)
        g = self.create_gig()

    def tearDown(self):
        """ make sure we get rid of anything we made """
        Member.objects.all().delete()
        Band.objects.all().delete()
        Assoc.objects.all().delete()
        Gig.objects.all().delete()

    def create_gig(self):
        the_date = timezone.datetime(2100,1,2,tzinfo=pytz.timezone(self.band.timezone))
        return Gig.objects.create(
            title="New Gig",
            band_id=self.band.id,
            date=the_date,
            setdate=the_date + timedelta(minutes=30),
            enddate=the_date + timedelta(hours=2)
        )

    def test_member_caldav_stream(self):
        cf = prepare_calfeed(self.joeuser)
        self.assertTrue(cf.startswith(b'BEGIN:VCALENDAR'))
        self.assertTrue(cf.find(b'g@h.i')>0)
        self.assertTrue(cf.endswith(b'END:VCALENDAR\r\n'))
        self.assertTrue(cf.find(b'EVENT')>0)
