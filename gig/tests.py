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
import copy
from django.core import mail
from django.test import TestCase, override_settings
from member.models import Member
from band.models import Band, Section, Assoc
from band.util import AssocStatusChoices
from .models import Gig
from .helpers import send_reminder_email
from go3 import settings
from datetime import timedelta, datetime, time
from django.utils import timezone

MISSING_TEMPLATES = copy.deepcopy(settings.TEMPLATES)
MISSING_TEMPLATES[0]['OPTIONS']['string_if_invalid'] = 'MISSING: %s'

class GigTest(TestCase):
    def setUp(self):
        self.super = Member.objects.create_user(email='a@b.c', is_superuser=True)
        self.band_admin = Member.objects.create_user(email='d@e.f')
        self.joeuser = Member.objects.create_user(email='g@h.i')
        self.janeuser = Member.objects.create_user(email='j@k.l')
        self.band = Band.objects.create(name='test band')
        Assoc.objects.create(member=self.band_admin, band=self.band, is_admin=True)

    def tearDown(self):
        """ make sure we get rid of anything we made """
        Member.objects.all().delete()
        Band.objects.all().delete()
        Assoc.objects.all().delete()

    def create_gig(self):
        return Gig.objects.create(
            title="New Gig",
            band_id=self.band.id,
            date=datetime(2100, 1, 2),
            calltime=time(12, tzinfo=timezone.get_current_timezone()),
            settime=time(12, 30, tzinfo=timezone.get_current_timezone()),
            endtime=time(14, tzinfo=timezone.get_current_timezone())
        )

    def test_no_section(self):
        """ show that the band has a default section called 'No Section' """
        a = self.band.assocs.first()
        s = a.default_section
        self.assertTrue(s.is_default)
        self.assertTrue(s.name, "No Section")


    def test_gig_plans(self):
        """ show that when a gig is created, every member has a plan """
        g = self.create_gig()
        self.assertEqual(g.plans.count(), self.band.assocs.count())

    def test_plan_section(self):
        """ show that when we have a gig plan, it uses the default section """
        s1 = Section.objects.create(name='s1', band=self.band)
        s2 = Section.objects.create(name='s2', band=self.band)
        s3 = Section.objects.create(name='s3', band=self.band)
        self.assertEqual(self.band.sections.count(), 4)

        """ make the band's first assoc default to s1 section """
        a = self.band.assocs.first()
        a.default_section = s1
        a.save()
        self.assertEqual(self.band_admin.assocs.first().default_section, s1)
        self.assertEqual(self.band_admin.assocs.first().section, s1)

        """ now create a gig and find out what the member's plan says """
        g = self.create_gig()
        p = g.plans.first()
        self.assertEqual(p.assoc.member, self.band_admin)
        self.assertEqual(p.plan_section, None) # we didn't set one so should be None
        self.assertEqual(p.section, s1) # should use the member's section

        """ change the member's default section and show that it changed for the gig """
        a.default_section=s2
        a.save()
        p = g.plans.first()
        self.assertEqual(p.section, s2) # should use the member's section

        """ now show we override it if we set the plan section """
        p.plan_section = s3
        p.save()
        p = g.plans.first()
        self.assertEqual(p.section, s3) # should use the override section

        """ now change the member's default but the plan should not change """
        a.default_section = s1
        a.save()
        p = g.plans.first()
        self.assertEqual(p.section, s3) # should use the override section

    @override_settings(TEMPLATES=MISSING_TEMPLATES)
    def test_new_gig_email(self):
        Assoc.objects.create(member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        g = self.create_gig()
        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]
        self.assertIn(g.title, message.subject)
        self.assertIn("01/02/2100 (Sat)", message.body)
        self.assertIn('noon (Call Time), 12:30 p.m. (Set Time), 2 p.m. (End Time)', message.body)
        self.assertIn('Unconfirmed', message.body)
        self.assertNotIn('MISSING', message.body)

    def test_new_gig_all_confirmed(self):
        Assoc.objects.create(member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        Assoc.objects.create(member=self.janeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        self.create_gig()
        self.assertEqual(len(mail.outbox), 2)

    def test_new_gig_obey_email_me(self):
        Assoc.objects.create(member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        Assoc.objects.create(member=self.janeuser, band=self.band, status=AssocStatusChoices.CONFIRMED, email_me=False)
        self.create_gig()
        self.assertEqual(len(mail.outbox), 1)

    def test_new_gig_contact(self):
        Assoc.objects.create(member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        Gig.objects.create(title="New Gig", band_id=self.band.id, date=timezone.now() + timedelta(days=1), contact=self.janeuser)

        message = mail.outbox[0]
        self.assertIn(self.janeuser.email, message.reply_to)
        self.assertIn(self.janeuser.display_name, message.body)

    def test_new_gig_localization(self):
        self.joeuser.preferences.language = 'de'
        self.joeuser.save()
        Assoc.objects.create(member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        self.create_gig()

        message = mail.outbox[0]
        self.assertIn('02.01.2100 (Sa)', message.body)
        self.assertIn('12:00 (Beginn), 12:30 (Termin), 14:00 (Ende)', message.body)
        self.assertIn('Nicht fixiert', message.body)

    def test_reminder_email(self):
        Assoc.objects.create(member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        g = self.create_gig()
        mail.outbox = []
        send_reminder_email(g)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn('Reminder', message.subject)
        self.assertIn('reminder', message.body)
