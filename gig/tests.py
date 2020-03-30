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
from django.test import TestCase, override_settings, RequestFactory
from member.models import Member
from band.models import Band, Section, Assoc
from band.util import AssocStatusChoices
from .models import Gig, Plan
from .helpers import send_reminder_email, send_snooze_reminders
from .forms import GigForm
from .views import CreateView, UpdateView
from go3 import settings
from datetime import timedelta, datetime, time
from django.urls import reverse
from django.utils import timezone
from pytz import timezone as pytz_timezone

MISSING_TEMPLATES = copy.deepcopy(settings.TEMPLATES)
MISSING_TEMPLATES[0]['OPTIONS']['string_if_invalid'] = 'MISSING: %s'

class GigTest(TestCase):
    def setUp(self):
        self.super = Member.objects.create_user(email='a@b.c', is_superuser=True)
        self.band_admin = Member.objects.create_user(email='d@e.f')
        self.joeuser = Member.objects.create_user(email='g@h.i')
        self.janeuser = Member.objects.create_user(email='j@k.l')
        self.band = Band.objects.create(name='test band', timezone='UTC', anyone_can_create_gigs=True)
        # Assoc.objects.create(member=self.band_admin, band=self.band, is_admin=True, status=AssocStatusChoices.CONFIRMED)

    def tearDown(self):
        """ make sure we get rid of anything we made """
        Member.objects.all().delete()
        Band.objects.all().delete()
        Assoc.objects.all().delete()

    def create_gig(self, the_member, start_date='auto', set_date='auto', end_date='auto'):
        thedate = timezone.datetime(2100,1,2, 12, tzinfo=pytz_timezone('UTC')) if start_date == 'auto' else start_date
        return Gig.objects.create(
            title="New Gig",
            band_id=self.band.id,
            date=thedate,
            setdate=thedate + timedelta(minutes=30) if set_date == 'auto' else set_date,
            enddate=thedate + timedelta(hours=2) if end_date == 'auto' else end_date,
            contact=the_member,
            status=Gig.StatusOptions.UNKNOWN
        )

    def create_gig_form(self, **kwargs):

        date = kwargs.get('date', timezone.datetime(2100,1,2, 12, tzinfo=pytz_timezone('UTC')))
        setdate = kwargs.get('setdate', date + timedelta(minutes=30))
        enddate = kwargs.get('enddate', date + timedelta(hours=2))

        f = GigForm(data={'title':'New Gig',
                          'date':date, 
                          'setdate':setdate,
                          'enddate':enddate,
                          'contact':kwargs.get('contact', self.joeuser),
                          'status':Gig.StatusOptions.UNKNOWN,
                          'send_update': True
                          })
        r = RequestFactory().get(f'/gig/create/{self.band.id}')
        r.user = kwargs.get('contact', self.joeuser)
        v = CreateView()
        v.setup(r, bk=self.band.id)
        v.form_valid(f)
        return v.object

    def update_gig_form(self, the_gig, **kwargs):
        data={
            'title':the_gig.title,
            'date':the_gig.date,
            'setdate':the_gig.setdate,
            'enddate':the_gig.enddate,
            'contact':the_gig.contact,
            'status':the_gig.status,
            'send_update':True
        }
        for x in kwargs.keys():
            data[x]=kwargs[x]

        f = GigForm(instance=the_gig, data=data)

        r = RequestFactory().get(f'/gig/{the_gig.id}/update/{self.band.id}')
        v = UpdateView()
        v.setup(r, bk=self.band.id)
        v.form_valid(f)
        return v.object

    def assoc_joe(self):
        a = Assoc.objects.create(member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        return a

    def assoc_joe_and_create_gig(self, **kwargs):
        a = self.assoc_joe()
        g = self.create_gig_form(contact=self.joeuser, **kwargs)
        p = g.member_plans.filter(assoc=a).get()
        return g, a, p

    def test_no_section(self):
        """ show that the band has a default section called 'No Section' """
        self.assoc_joe()
        a = self.band.assocs.first()
        s = a.default_section
        self.assertTrue(s.is_default)
        self.assertTrue(s.name, "No Section")


    def test_gig_plans(self):
        """ show that when a gig is created, every member has a plan """
        g = self.create_gig_form(contact=self.joeuser)
        self.assertEqual(g.plans.count(), self.band.assocs.count())

    def test_plan_section(self):
        """ show that when we have a gig plan, it uses the default section """
        s1 = Section.objects.create(name='s1', band=self.band)
        s2 = Section.objects.create(name='s2', band=self.band)
        s3 = Section.objects.create(name='s3', band=self.band)
        self.assertEqual(self.band.sections.count(), 4)

        """ make the band's first assoc default to s1 section """
        self.assoc_joe()
        a = self.band.assocs.first()
        a.default_section = s1
        a.save()
        self.assertEqual(self.joeuser.assocs.first().default_section, s1)
        self.assertEqual(self.joeuser.assocs.first().section, s1)

        """ now create a gig and find out what the member's plan says """
        g = self.create_gig(self.band_admin)
        p = g.member_plans.get(assoc__member=self.joeuser)
        self.assertEqual(p.assoc.member, self.joeuser)
        self.assertEqual(p.plan_section, None) # we didn't set one so should be None
        self.assertEqual(p.section, s1) # should use the member's section

        """ change the member's default section and show that it changed for the gig """
        a.default_section=s2
        a.save()
        p = g.plans.get(assoc__member=a.member)
        self.assertEqual(p.section, s2) # should use the member's section

        """ now show we override it if we set the plan section """
        p.plan_section = s3
        p.save()
        p = g.plans.get(assoc__member=p.assoc.member)
        self.assertEqual(p.section, s3) # should use the override section

        """ now change the member's default but the plan should not change """
        a.default_section = s1
        a.save()
        p = g.plans.get(assoc__member=a.member)
        self.assertEqual(p.section, s3) # should use the override section

    def test_gig_create_permissions(self):
        """ make sure that if I don't have permission to create a gig, I can't """
        self.band.anyone_can_create_gigs = False
        self.band.save()
        with self.assertRaises(PermissionError):
            self.create_gig_form(contact=self.janeuser)

    @override_settings(TEMPLATES=MISSING_TEMPLATES)
    def test_new_gig_email(self):
        g, a, p = self.assoc_joe_and_create_gig()
        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]
        self.assertIn(g.title, message.subject)
        self.assertIn("01/02/2100 (Sat)", message.body)
        self.assertIn('noon (Call Time), 12:30 p.m. (Set Time), 2 p.m. (End Time)', message.body)
        self.assertIn('Unconfirmed', message.body)
        self.assertIn(f'{p.id}/{Plan.StatusChoices.DEFINITELY}', message.body)
        self.assertIn(f'{p.id}/{Plan.StatusChoices.CANT_DO_IT}', message.body)
        self.assertIn(f'{p.id}/{Plan.StatusChoices.DONT_KNOW}', message.body)
        self.assertNotIn('MISSING', message.subject)
        self.assertNotIn('MISSING', message.body)

    def test_new_gig_all_confirmed(self):
        Assoc.objects.create(member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        Assoc.objects.create(member=self.janeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        self.create_gig_form(contact=self.joeuser)
        self.assertEqual(len(mail.outbox), 2)

    def test_new_gig_obey_email_me(self):
        Assoc.objects.create(member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        Assoc.objects.create(member=self.janeuser, band=self.band, status=AssocStatusChoices.CONFIRMED, email_me=False)
        self.create_gig_form(contact=self.joeuser)
        self.assertEqual(len(mail.outbox), 1)

    def test_gig_time_no_set(self):
        self.assoc_joe_and_create_gig(setdate=None)
        self.assertIn('Time: noon (Call Time), 2 p.m. (End Time)\nContact', mail.outbox[0].body)

    def test_gig_time_no_end(self):
        self.assoc_joe_and_create_gig(enddate=None)
        self.assertIn('Time: noon (Call Time), 12:30 p.m. (Set Time)\nContact', mail.outbox[0].body)

    def test_gig_time_no_set_no_end(self):
        self.assoc_joe_and_create_gig(setdate=None, enddate=None)
        self.assertIn('Time: noon (Call Time)\nContact', mail.outbox[0].body)

    def test_gig_time_long_set(self):
        date = timezone.datetime(2100, 1, 2, 12, tzinfo=pytz_timezone(self.band.timezone))
        self.assoc_joe_and_create_gig(date=date, setdate=date + timedelta(days=1), enddate=None)
        self.assertIn('Call Time: 01/02/2100 noon (Sat)\nSet Time: 01/03/2100 noon (Sun)\nContact', mail.outbox[0].body)

    def test_gig_time_long_end(self):
        date = timezone.datetime(2100, 1, 2, 12, tzinfo=pytz_timezone(self.band.timezone))
        self.assoc_joe_and_create_gig(date=date, setdate=None, enddate=date + timedelta(days=1))
        self.assertIn('Call Time: 01/02/2100 noon (Sat)\nEnd Time: 01/03/2100 noon (Sun)\nContact', mail.outbox[0].body)

    def test_gig_time_long_set_end(self):
        date = timezone.datetime(2100, 1, 2, 12, tzinfo=pytz_timezone(self.band.timezone))
        self.assoc_joe_and_create_gig(date=date, setdate=date + timedelta(days=1), enddate=date+timedelta(days=1, hours=1))
        self.assertIn('Call Time: 01/02/2100 noon (Sat)\nSet Time: 01/03/2100 noon (Sun)\nEnd Time: 01/03/2100 1 p.m. (Sun)\nContact', mail.outbox[0].body)

    def test_new_gig_contact(self):
        self.assoc_joe_and_create_gig()

        message = mail.outbox[0]
        self.assertIn(self.joeuser.email, message.reply_to)
        self.assertIn(self.joeuser.display_name, message.body)

    def test_new_gig_localization(self):
        self.joeuser.preferences.language = 'de'
        self.joeuser.save()
        self.assoc_joe_and_create_gig()

        message = mail.outbox[0]
        self.assertIn('02.01.2100 (Sa)', message.body)
        self.assertIn('12:00 (Beginn), 12:30 (Termin), 14:00 (Ende)', message.body)
        self.assertIn('Nicht fixiert', message.body)

    def test_new_gig_time_localization(self):
        self.joeuser.preferences.language='en-US'
        self.joeuser.save()
        self.band.timezone = 'America/New_York'
        self.band.save()
        # Assoc.objects.create(member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        # g = self.create_gig()
        self.assoc_joe_and_create_gig()
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn("01/02/2100 (Sat)", message.body)
        self.assertIn('7 a.m. (Call Time), 7:30 a.m. (Set Time), 9 a.m. (End Time)', message.body)

    def test_gig_time_daylight_savings(self):
        self.band.timezone = 'America/New_York'
        self.band.save()
        Assoc.objects.create(member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)

        # DST information only out to 2037?
        self.create_gig_form(date=timezone.datetime(2037, 1, 2, 12, tzinfo=pytz_timezone('UTC')))
        self.create_gig_form(date=timezone.datetime(2037, 7, 2, 12, tzinfo=pytz_timezone('UTC')))
        self.assertIn('7 a.m. (Call Time)', mail.outbox[0].body)
        self.assertIn('8 a.m. (Call Time)', mail.outbox[1].body)


    @override_settings(TEMPLATES=MISSING_TEMPLATES)
    def test_reminder_email(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        mail.outbox = []
        send_reminder_email(g)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn('Reminder', message.subject)
        self.assertIn('reminder', message.body)
        self.assertNotIn('MISSING', message.subject)
        self.assertNotIn('MISSING', message.body)

    def test_no_reminder_to_decided(self):
        g, a, p = self.assoc_joe_and_create_gig()
        p.status = Plan.StatusChoices.DEFINITELY
        p.save()
        mail.outbox = []
        send_reminder_email(g)

        self.assertEqual(len(mail.outbox), 0)

    def test_snooze_reminder(self):
        Assoc.objects.create(member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        Assoc.objects.create(member=self.janeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        g = self.create_gig_form()
        g.member_plans.update(snooze_until=datetime.now(tz=timezone.get_current_timezone()))
        mail.outbox = []
        send_snooze_reminders()

        self.assertEqual(len(mail.outbox), 2)
        for message in mail.outbox:
            self.assertIn('Reminder', message.subject)
        self.assertEqual(g.member_plans.filter(snooze_until__isnull=False).count(), 0)

    def test_snooze_until_cutoff(self):
        joeassoc = Assoc.objects.create(member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        janeassoc=Assoc.objects.create(member=self.janeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        g = self.create_gig_form()
        now = datetime.now(tz=timezone.get_current_timezone())
        g.member_plans.filter(assoc=joeassoc).update(snooze_until=now)
        g.member_plans.filter(assoc=janeassoc).update(snooze_until=now + timedelta(days=2))
        mail.outbox = []
        send_snooze_reminders()

        self.assertEqual(len(mail.outbox), 1)

    def test_snooze_until_null(self):
        a = Assoc.objects.create(member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        Assoc.objects.create(member=self.janeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        g = self.create_gig_form()
        now = datetime.now(tz=timezone.get_current_timezone())
        g.member_plans.filter(assoc=a).update(snooze_until=now)
        mail.outbox = []
        send_snooze_reminders()

        self.assertEqual(len(mail.outbox), 1)

    @override_settings(TEMPLATES=MISSING_TEMPLATES)
    def test_gig_edit_email(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        mail.outbox = []
        g.status = g.StatusOptions.CONFIRMED
        g.save()
        self.update_gig_form(g)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn('Edit', message.subject)
        self.assertNotIn('Your current status', message.body)
        self.assertIn('**can** make it', message.body)
        self.assertIn("**can't** make it", message.body)
        self.assertNotIn('MISSING', message.subject)
        self.assertNotIn('MISSING', message.body)

    def test_gig_edit_status(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        mail.outbox = []
        self.update_gig_form(g, status=g.StatusOptions.CONFIRMED)

        message = mail.outbox[0]
        self.assertIn('Status', message.subject)
        self.assertIn('Confirmed!', message.body)
        self.assertIn("(was Unconfirmed)", message.body)

    def test_gig_edit_call(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        mail.outbox = []
        self.update_gig_form(g, date=g.date + timedelta(hours=2), enddate=None, setdate=None)


        message = mail.outbox[0]
        self.assertIn('Call Time', message.subject)
        self.assertIn('2 p.m.', message.body)
        self.assertIn("(was noon)", message.body)

    def test_gig_edit_add_time(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        self.update_gig_form(g, setdate=None)

        mail.outbox = []
        self.update_gig_form(g, setdate=g.date + timedelta(hours=2))

        message = mail.outbox[0]
        self.assertIn('Set Time', message.subject)
        self.assertIn('2 p.m.', message.body)
        self.assertIn("(was not set)", message.body)

    def test_gig_edit_contact(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        mail.outbox = []
        self.update_gig_form(g, contact=self.janeuser)

        message = mail.outbox[0]
        self.assertIn('Contact', message.subject)
        self.assertIn(self.janeuser.display_name, message.body)
        self.assertIn(f"(was {self.joeuser.display_name})", message.body)

    def test_gig_edit_trans(self):
        self.joeuser.preferences.language = 'de'
        self.joeuser.save()
        g, _, _ = self.assoc_joe_and_create_gig()
        mail.outbox = []
        self.update_gig_form(g, date=g.date + timedelta(hours=2), enddate=None, setdate=None)

        message = mail.outbox[0]
        self.assertIn('Beginn', message.subject)
        # We need to check the previous time, since the current time will show
        # up in the details block, which we're already checking to be localized
        self.assertIn('12:00', message.body)

    def test_gig_edit_definitely(self):
        g, a, p = self.assoc_joe_and_create_gig()
        p.status = Plan.StatusChoices.DEFINITELY
        p.save()
        mail.outbox = []
        self.update_gig_form(g, status=g.StatusOptions.CONFIRMED)

        message = mail.outbox[0]
        self.assertIn(f'Your current status is "{Plan.StatusChoices.DEFINITELY.label}"', message.body)
        self.assertNotIn('**can** make it', message.body)
        self.assertIn("**can't** make it", message.body)

    def test_gig_edit_cant(self):
        g, a, p = self.assoc_joe_and_create_gig()
        p.status = Plan.StatusChoices.CANT_DO_IT
        p.save()
        mail.outbox = []
        self.update_gig_form(g, status=g.StatusOptions.CONFIRMED)

        message = mail.outbox[0]
        self.assertIn(f'Your current status is "{Plan.StatusChoices.CANT_DO_IT.label}"', message.body)
        self.assertIn('**can** make it', message.body)
        self.assertNotIn("**can't** make it", message.body)

    def test_answer_yes(self):
        _, _, p = self.assoc_joe_and_create_gig()
        response = self.client.get(reverse('gig-answer', args=[p.id, Plan.StatusChoices.DEFINITELY]))
        p.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(p.status, Plan.StatusChoices.DEFINITELY)
        self.assertEqual(p.snooze_until, None)

    def test_answer_no(self):
        _, _, p = self.assoc_joe_and_create_gig()
        response = self.client.get(reverse('gig-answer', args=[p.id, Plan.StatusChoices.CANT_DO_IT]))
        p.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(p.status, Plan.StatusChoices.CANT_DO_IT)
        self.assertEqual(p.snooze_until, None)

    def test_answer_snooze_long(self):
        now = datetime.now(tz=timezone.get_current_timezone())
        _, _, p = self.assoc_joe_and_create_gig()
        response = self.client.get(reverse('gig-answer', args=[p.id, Plan.StatusChoices.DONT_KNOW]))
        p.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(p.status, Plan.StatusChoices.DONT_KNOW)
        self.assertGreaterEqual((p.snooze_until - now).days, 7)

    def test_answer_snooze_short(self):
        now = datetime.now(tz=timezone.get_current_timezone())
        g, _, p = self.assoc_joe_and_create_gig()
        g.date = now.date() + timedelta(days=3)
        response = self.client.get(reverse('gig-answer', args=[p.id, Plan.StatusChoices.DONT_KNOW]))
        p.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(p.status, Plan.StatusChoices.DONT_KNOW)
        self.assertLessEqual((p.snooze_until - now).days, 7)

    def test_answer_snooze_too_short(self):
        now = datetime.now(tz=timezone.get_current_timezone())
        g, _, p = self.assoc_joe_and_create_gig()
        g.date = timezone.now() + timedelta(days=1)
        g.save()
        response = self.client.get(reverse('gig-answer', args=[p.id, Plan.StatusChoices.DONT_KNOW]))
        p.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(p.status, Plan.StatusChoices.DONT_KNOW)
        self.assertEqual(p.snooze_until, None)

    def test_answer_unsets_snooze_until(self):
        now = datetime.now(tz=timezone.get_current_timezone())
        _, _, p = self.assoc_joe_and_create_gig()
        p.status = Plan.StatusChoices.DONT_KNOW
        p.snooze_until = now
        p.save()

        p.status = Plan.StatusChoices.DEFINITELY
        p.save()
        p.refresh_from_db()
        self.assertEqual(p.snooze_until, None)
