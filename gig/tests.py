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
from django.test import TestCase, RequestFactory, Client
from member.models import Member
from band.models import Band, Section, Assoc
from band.util import AssocStatusChoices
from gig.util import GigStatusChoices, PlanStatusChoices
from .models import Gig, Plan, GigComment
from .helpers import send_reminder_email
from .tasks import send_snooze_reminders
from .forms import GigForm
from .views import CreateView, UpdateView
from .tasks import archive_old_gigs
from go3 import settings
from datetime import timedelta, datetime, time
from django.urls import reverse
from django.utils import timezone
from pytz import timezone as pytz_timezone
from lib.template_test import MISSING, flag_missing_vars


class GigTestBase(TestCase):
    def setUp(self):
        self.super = Member.objects.create_user(email="super@b.c", is_superuser=True)
        self.band_admin = Member.objects.create_user(email="admin@e.f")
        self.joeuser = Member.objects.create_user(email="joeuser@h.i")
        self.janeuser = Member.objects.create_user(email="janeuser@k.l")
        self.band = Band.objects.create(
            name="test band",
            timezone="UTC",
            anyone_can_create_gigs=True,
            hometown="Seattle",
        )
        Assoc.objects.create(
            member=self.band_admin,
            band=self.band,
            is_admin=True,
            status=AssocStatusChoices.CONFIRMED,
            email_me=False,
        )

    def tearDown(self):
        """make sure we get rid of anything we made"""
        Member.objects.all().delete()
        Band.objects.all().delete()
        Assoc.objects.all().delete()

    def create_gig(
        self,
        the_member,
        title="New Gig",
        start_date="auto",
        set_date="auto",
        end_date="auto",
    ):
        thedate = (
            timezone.datetime(2100, 1, 2, 12, tzinfo=pytz_timezone("UTC"))
            if start_date == "auto"
            else start_date
        )
        return Gig.objects.create(
            title=title,
            band_id=self.band.id,
            date=thedate,
            setdate=thedate + timedelta(minutes=30) if set_date == "auto" else set_date,
            enddate=thedate + timedelta(hours=2) if end_date == "auto" else end_date,
            contact=the_member,
            status=GigStatusChoices.UNKNOWN,
        )

    def create_gig_form(
        self,
        user=None,
        expect_code=302,
        call_date="01/02/2100",
        set_date="",
        end_date="",
        call_time="12:00 pm",
        set_time="",
        end_time="",
        title="New Gig",
        **kwargs,
    ):

        status = kwargs.pop("status", GigStatusChoices.UNKNOWN)
        contact = kwargs.pop("contact", self.joeuser).id
        send_update = kwargs.pop("send_update", True)

        c = Client()
        c.force_login(user if user else self.joeuser)
        response = c.post(
            f"/gig/create/{self.band.id}",
            {
                "title": title,
                "call_date": call_date,
                "call_time": call_time,
                "set_date": set_date,
                "set_time": set_time,
                "end_date": end_date,
                "end_time": end_time,
                "contact": contact,
                "status": status,
                "send_update": send_update,
                **kwargs,
            },
        )

        self.assertEqual(
            response.status_code, expect_code
        )  # should get a redirect to the gig info page
        obj = Gig.objects.last()
        return obj

    def _dateformat(self, x):
        return x.strftime("%m/%d/%Y") if x else ""

    def _timeformat(self, x):
        return x.strftime("%I:%M %p") if x else ""

    def update_gig_form(self, the_gig, expect_code=302, **kwargs):

        call_date = kwargs.pop("call_date", self._dateformat(the_gig.date))
        end_date = kwargs.pop("end_date", self._dateformat(the_gig.enddate))
        call_time = kwargs.pop("call_time", self._timeformat(the_gig.date))
        set_time = kwargs.pop("set_time", self._timeformat(the_gig.setdate))
        end_time = kwargs.pop("end_time", self._timeformat(the_gig.enddate))

        data = {
            "title": the_gig.title,
            "call_date": call_date,
            "end_date": end_date,
            "call_time": call_time,
            "set_time": set_time,
            "end_time": end_time,
            "contact": the_gig.contact.id,
            "status": the_gig.status,
            "send_update": True,
        }
        for x in kwargs.keys():
            data[x] = kwargs[x]

        c = Client()
        c.force_login(self.joeuser)
        response = c.post(f"/gig/{the_gig.id}/update", data)
        self.assertEqual(
            response.status_code, expect_code
        )  # should get a redirect to the gig info page
        self.assertEqual(Gig.objects.count(), 1)
        the_gig.refresh_from_db()
        return the_gig

    def assoc_user(self, user):
        a = Assoc.objects.create(
            member=user, band=self.band, status=AssocStatusChoices.CONFIRMED
        )
        return a

    def assoc_joe_and_create_gig(self, **kwargs):
        a = self.assoc_user(self.joeuser)
        g = self.create_gig_form(contact=self.joeuser, **kwargs)
        p = g.member_plans.filter(assoc=a).get() if g else None
        return g, a, p


class GigTest(GigTestBase):
    def test_no_section(self):
        """show that the band has a default section called 'No Section'"""
        self.assoc_user(self.joeuser)
        a = self.band.assocs.first()
        s = a.default_section
        self.assertTrue(s.is_default)
        self.assertTrue(s.name, "No Section")

    def test_gig_plans(self):
        """show that when a gig is created, every member has a plan"""
        self.assoc_user(self.joeuser)
        g = self.create_gig_form()
        self.assertEqual(g.plans.count(), self.band.assocs.count())

    def test_plan_section(self):
        """show that when we have a gig plan, it uses the default section"""
        s1 = Section.objects.create(name="s1", band=self.band)
        s2 = Section.objects.create(name="s2", band=self.band)
        s3 = Section.objects.create(name="s3", band=self.band)
        self.assertEqual(self.band.sections.count(), 4)

        """ make the band's first assoc default to s1 section """
        a = self.assoc_user(self.joeuser)
        a.default_section = s1
        a.save()
        self.assertEqual(self.joeuser.assocs.first().default_section, s1)
        self.assertEqual(self.joeuser.assocs.first().section, s1)

        """ now create a gig and find out what the member's plan says """
        g = self.create_gig(self.band_admin)
        p = g.member_plans.get(assoc__member=self.joeuser)
        self.assertEqual(p.assoc.member, self.joeuser)
        # we didn't set one so should be None
        self.assertEqual(p.plan_section, None)
        self.assertEqual(p.section, s1)  # should use the member's section

        """ change the member's default section and show that it changed for the gig """
        a.default_section = s2
        a.save()
        p = g.plans.get(assoc__member=a.member)
        self.assertEqual(p.section, s2)  # should use the member's section

        """ now show we override it if we set the plan section """
        p.plan_section = s3
        p.save()
        p = g.plans.get(assoc__member=p.assoc.member)
        self.assertEqual(p.section, s3)  # should use the override section

        """ now change the member's default but the plan should not change """
        a.default_section = s1
        a.save()
        p = g.plans.get(assoc__member=a.member)
        self.assertEqual(p.section, s3)  # should use the override section

    def test_deleting_section(self):
        """show that if we delete a section which has been selected as a plan override
        that the plan section is set back to the user's default section, not the
        band's default section"""

        s1 = Section.objects.create(name="s1", band=self.band)
        s2 = Section.objects.create(name="s2", band=self.band)

        # set joe's default section to s1
        a = self.assoc_user(self.joeuser)
        a.default_section = s1
        a.save()

        g = self.create_gig(self.band_admin)
        p = g.member_plans.get(assoc__member=self.joeuser)
        # we didn't set one so should be None
        self.assertEqual(p.plan_section, None)
        self.assertEqual(p.section, s1)  # should use the member's section

        # override the section in the plan
        p.plan_section = s2
        p.save()
        p.refresh_from_db()
        self.assertEqual(p.section, s2)  # should be using the override

        # now delete the override section
        s2.delete()
        p.refresh_from_db()
        self.assertEqual(p.section, s1)  # should revert to joe's default

    def test_gig_create_permissions(self):
        """make sure that if I don't have permission to create a gig, I can't"""
        self.band.anyone_can_create_gigs = False
        self.band.save()
        # need a member of the band so there's a valid contact to select from in the form
        self.assoc_user(self.joeuser)
        self.create_gig_form(
            user=self.janeuser, title="permission gig", expect_code=403
        )

    def test_gig_edit_permissions(self):
        """make sure that if I don't have permission to edit a gig, I can't"""
        g, _, _ = self.assoc_joe_and_create_gig(
            set_time="12:30 pm", end_time="02:00 pm"
        )
        self.band.anyone_can_manage_gigs = False
        self.band.save()
        self.update_gig_form(g, user=self.janeuser, title="not legal!", expect_code=403)

    @flag_missing_vars
    def test_new_gig_email(self):
        g, _, p = self.assoc_joe_and_create_gig(
            set_time="12:30 pm", end_time="02:00 pm"
        )
        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]
        self.assertIn(g.title, message.subject)
        self.assertIn("01/02/2100 (Sat)", message.body)
        self.assertIn(
            "noon (Call Time), 12:30 p.m. (Set Time), 2 p.m. (End Time)", message.body
        )
        self.assertIn("Unconfirmed", message.body)
        self.assertIn(f"{p.id}/{PlanStatusChoices.DEFINITELY}", message.body)
        self.assertIn(f"{p.id}/{PlanStatusChoices.CANT_DO_IT}", message.body)
        self.assertIn(f"{p.id}/{PlanStatusChoices.DONT_KNOW}", message.body)
        self.assertNotIn(MISSING, message.subject)
        self.assertNotIn(MISSING, message.body)

    def test_new_gig_all_confirmed(self):
        Assoc.objects.create(
            member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED
        )
        Assoc.objects.create(
            member=self.janeuser, band=self.band, status=AssocStatusChoices.CONFIRMED
        )
        self.create_gig_form(contact=self.joeuser)
        self.assertEqual(len(mail.outbox), 2)

    def test_new_gig_obey_email_me(self):
        Assoc.objects.create(
            member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED
        )
        Assoc.objects.create(
            member=self.janeuser,
            band=self.band,
            status=AssocStatusChoices.CONFIRMED,
            email_me=False,
        )
        self.create_gig_form(contact=self.joeuser)
        self.assertEqual(len(mail.outbox), 1)

    def test_gig_time_no_set(self):
        self.assoc_joe_and_create_gig(set_time="", end_time="02:00 pm")
        self.assertIn(
            "Time: noon (Call Time), 2 p.m. (End Time)\nContact", mail.outbox[0].body
        )

    def test_gig_time_no_end(self):
        self.assoc_joe_and_create_gig(set_time="12:30 pm", end_date="", end_time="")
        self.assertIn(
            "Time: noon (Call Time), 12:30 p.m. (Set Time)\nContact",
            mail.outbox[0].body,
        )

    def test_gig_time_no_set_no_end(self):
        self.assoc_joe_and_create_gig(set_time="", end_date="", end_time="")
        self.assertIn("Time: noon (Call Time)\nContact", mail.outbox[0].body)

    def test_gig_time_long_end(self):
        date = timezone.datetime(
            2100, 1, 2, 12, tzinfo=pytz_timezone(self.band.timezone)
        )
        enddate = date + timedelta(days=1)
        self.assoc_joe_and_create_gig(
            call_date=self._dateformat(date),
            call_time=self._timeformat(date),
            set_time="",
            end_date=self._dateformat(enddate),
            end_time=self._timeformat(enddate),
        )
        self.assertIn(
            "Call Time: 01/02/2100 midnight (Sat)\nEnd Time: 01/03/2100 midnight (Sun)\nContact",
            mail.outbox[0].body,
        )

    def test_new_gig_contact(self):
        self.assoc_joe_and_create_gig()

        message = mail.outbox[0]
        self.assertIn(self.joeuser.email, message.reply_to)
        self.assertIn(self.joeuser.display_name, message.body)

    def test_new_gig_localization(self):
        self.joeuser.preferences.language = "de"
        self.joeuser.save()
        self.assoc_joe_and_create_gig(set_time="12:30 pm", end_time="2:00 pm")

        message = mail.outbox[0]
        self.assertIn("02.01.2100 (Sa)", message.body)
        self.assertIn("12:00 (Beginn), 12:30 (Termin), 14:00 (Ende)", message.body)
        self.assertIn("Nicht fixiert", message.body)

    def test_new_gig_time_localization(self):
        self.joeuser.preferences.language = "en-US"
        self.joeuser.save()
        g, _, _ = self.assoc_joe_and_create_gig(
            set_time="12:30 pm", end_time="02:00 pm"
        )
        message = mail.outbox[0]
        mail.outbox = []
        self.band.timezone = "America/New_York"
        self.band.save()
        self.update_gig_form(g, title="new")
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn("01/02/2100 (Sat)", message.body)
        self.assertIn(
            "noon (Call Time), 12:30 p.m. (Set Time), 2 p.m. (End Time)", message.body
        )

    def test_gig_time_daylight_savings(self):
        """
        check to see that gig times are rendered correctly when going from UTC in the
        database to something else.
        """
        self.band.timezone = "UTC"
        self.band.save()
        Assoc.objects.create(
            member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED
        )
        date1 = timezone.datetime(2037, 1, 2, 12, tzinfo=pytz_timezone("UTC"))
        date2 = timezone.datetime(2037, 7, 2, 12, tzinfo=pytz_timezone("UTC"))
        self.create_gig_form(
            call_date=self._dateformat(date1), call_time=self._timeformat(date1)
        )
        self.create_gig_form(
            call_date=self._dateformat(date2), call_time=self._timeformat(date2)
        )

        # get the gigs we just made
        gigs = Gig.objects.order_by("id")
        first, second = gigs

        c = Client()
        c.force_login(self.joeuser)
        response = c.get(f"/gig/{first.id}/")
        self.assertIn("noon", response.content.decode("ascii"))

        # now change the band's timezone and render again
        self.band.timezone = "America/New_York"
        self.band.save()

        response = c.get(f"/gig/{first.id}/")
        self.assertIn("7 a.m.", response.content.decode("ascii"))
        response = c.get(f"/gig/{second.id}/")
        self.assertIn("8 a.m.", response.content.decode("ascii"))

    @flag_missing_vars
    def test_reminder_email(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        mail.outbox = []
        send_reminder_email(g)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn("Reminder", message.subject)
        self.assertIn("reminder", message.body)
        self.assertNotIn(MISSING, message.subject)
        self.assertNotIn(MISSING, message.body)

    def test_no_reminder_to_decided(self):
        g, _, p = self.assoc_joe_and_create_gig()
        p.status = PlanStatusChoices.DEFINITELY
        p.save()
        mail.outbox = []
        send_reminder_email(g)

        self.assertEqual(len(mail.outbox), 0)

    def test_reminder_url(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        mail.outbox = []
        self.client.force_login(self.band_admin)
        response = self.client.get(reverse("gig-remind", args=[g.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn("Reminder", message.subject)
        self.assertIn("reminder", message.body)
        self.assertNotIn(MISSING, message.subject)
        self.assertNotIn(MISSING, message.body)

    def test_snooze_reminder(self):
        Assoc.objects.create(
            member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED
        )
        Assoc.objects.create(
            member=self.janeuser, band=self.band, status=AssocStatusChoices.CONFIRMED
        )
        g = self.create_gig_form()
        g.member_plans.update(
            snooze_until=datetime.now(tz=timezone.get_current_timezone())
        )
        mail.outbox = []
        send_snooze_reminders()

        self.assertEqual(len(mail.outbox), 2)
        for message in mail.outbox:
            self.assertIn("Reminder", message.subject)
        self.assertEqual(g.member_plans.filter(snooze_until__isnull=False).count(), 0)

    def test_snooze_until_cutoff(self):
        joeassoc = Assoc.objects.create(
            member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED
        )
        janeassoc = Assoc.objects.create(
            member=self.janeuser, band=self.band, status=AssocStatusChoices.CONFIRMED
        )
        g = self.create_gig_form()
        now = datetime.now(tz=timezone.get_current_timezone())
        g.member_plans.filter(assoc=joeassoc).update(snooze_until=now)
        g.member_plans.filter(assoc=janeassoc).update(
            snooze_until=now + timedelta(days=2)
        )
        mail.outbox = []
        send_snooze_reminders()

        self.assertEqual(len(mail.outbox), 1)

    def test_snooze_until_null(self):
        a = Assoc.objects.create(
            member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED
        )
        Assoc.objects.create(
            member=self.janeuser, band=self.band, status=AssocStatusChoices.CONFIRMED
        )
        g = self.create_gig_form()
        now = datetime.now(tz=timezone.get_current_timezone())
        g.member_plans.filter(assoc=a).update(snooze_until=now)
        mail.outbox = []
        send_snooze_reminders()

        self.assertEqual(len(mail.outbox), 1)

    @flag_missing_vars
    def test_gig_edit_email(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        mail.outbox = []
        g.status = GigStatusChoices.CONFIRMED
        g.save()
        self.update_gig_form(g)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn("Edit", message.subject)
        self.assertNotIn("Your current status", message.body)
        self.assertIn("**can** make it", message.body)
        self.assertIn("**can't** make it", message.body)
        self.assertNotIn(MISSING, message.subject)
        self.assertNotIn(MISSING, message.body)

    def test_gig_edit_status(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        mail.outbox = []
        self.update_gig_form(g, status=GigStatusChoices.CONFIRMED)

        message = mail.outbox[0]
        self.assertIn("Status", message.subject)
        self.assertIn("Confirmed!", message.body)
        self.assertIn("(was Unconfirmed)", message.body)

    def test_gig_edit_call(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        mail.outbox = []
        newcalldate = g.date + timedelta(hours=2)
        self.update_gig_form(
            g,
            call_date=self._dateformat(newcalldate),
            call_time=self._timeformat(newcalldate),
            end_date="",
            end_time="",
            set_time="",
        )

        message = mail.outbox[0]
        self.assertIn("Call Time", message.subject)
        self.assertIn("2 p.m.", message.body)
        self.assertIn("(was noon)", message.body)

    def test_gig_edit_add_time(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        self.update_gig_form(g)

        mail.outbox = []
        settime = g.date + timedelta(hours=2)
        self.update_gig_form(
            g, set_date=self._dateformat(settime), set_time=self._timeformat(settime)
        )

        message = mail.outbox[0]
        self.assertIn("Set Time", message.subject)
        self.assertIn("2 p.m.", message.body)
        self.assertIn("(was not set)", message.body)

    def test_gig_edit_contact(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        mail.outbox = []
        self.update_gig_form(g, contact=self.janeuser.id)

        message = mail.outbox[0]
        self.assertIn("Contact", message.subject)
        self.assertIn(self.janeuser.display_name, message.body)
        self.assertIn(f"(was {self.joeuser.display_name})", message.body)

    def test_gig_edit_trans(self):
        self.joeuser.preferences.language = "de"
        self.joeuser.save()
        g, _, _ = self.assoc_joe_and_create_gig()
        mail.outbox = []
        newdate = g.date + timedelta(hours=2)
        self.update_gig_form(
            g,
            call_date=self._dateformat(newdate),
            call_time=self._timeformat(newdate),
            end_date="",
            end_time="",
            set_date="",
        )

        message = mail.outbox[0]
        self.assertIn("Beginn", message.subject)
        # We need to check the previous time, since the current time will show
        # up in the details block, which we're already checking to be localized
        self.assertIn("12:00", message.body)

    def test_gig_edit_definitely(self):
        g, _, p = self.assoc_joe_and_create_gig()
        p.status = PlanStatusChoices.DEFINITELY
        p.save()
        mail.outbox = []
        self.update_gig_form(g, status=GigStatusChoices.CONFIRMED)

        message = mail.outbox[0]
        self.assertIn(
            f'Your current status is "{PlanStatusChoices.DEFINITELY.label}"',  # pylint: disable=no-member
            message.body,
        )
        self.assertNotIn("**can** make it", message.body)
        self.assertIn("**can't** make it", message.body)

    def test_gig_edit_cant(self):
        g, _, p = self.assoc_joe_and_create_gig()
        p.status = PlanStatusChoices.CANT_DO_IT
        p.save()
        mail.outbox = []
        self.update_gig_form(g, status=GigStatusChoices.CONFIRMED)

        message = mail.outbox[0]
        self.assertIn(
            f'Your current status is "{PlanStatusChoices.CANT_DO_IT.label}"',  # pylint: disable=no-member
            message.body,
        )
        self.assertIn("**can** make it", message.body)
        self.assertNotIn("**can't** make it", message.body)

    def test_answer_yes(self):
        _, _, p = self.assoc_joe_and_create_gig()
        response = self.client.get(
            reverse("gig-answer", args=[p.id, PlanStatusChoices.DEFINITELY])
        )
        p.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(p.status, PlanStatusChoices.DEFINITELY)
        self.assertEqual(p.snooze_until, None)

    def test_answer_no(self):
        _, _, p = self.assoc_joe_and_create_gig()
        response = self.client.get(
            reverse("gig-answer", args=[p.id, PlanStatusChoices.CANT_DO_IT])
        )
        p.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(p.status, PlanStatusChoices.CANT_DO_IT)
        self.assertEqual(p.snooze_until, None)

    def test_answer_snooze_long(self):
        now = datetime.now(tz=timezone.get_current_timezone())
        _, _, p = self.assoc_joe_and_create_gig()
        response = self.client.get(
            reverse("gig-answer", args=[p.id, PlanStatusChoices.DONT_KNOW])
        )
        p.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(p.status, PlanStatusChoices.DONT_KNOW)
        self.assertGreaterEqual((p.snooze_until - now).days, 7)

    def test_answer_snooze_short(self):
        now = datetime.now(tz=timezone.get_current_timezone())
        g, _, p = self.assoc_joe_and_create_gig()
        g.date = now.date() + timedelta(days=3)
        response = self.client.get(
            reverse("gig-answer", args=[p.id, PlanStatusChoices.DONT_KNOW])
        )
        p.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(p.status, PlanStatusChoices.DONT_KNOW)
        self.assertLessEqual((p.snooze_until - now).days, 7)

    def test_answer_snooze_too_short(self):
        g, _, p = self.assoc_joe_and_create_gig()
        g.date = timezone.now() + timedelta(days=1)
        g.save()
        response = self.client.get(
            reverse("gig-answer", args=[p.id, PlanStatusChoices.DONT_KNOW])
        )
        p.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(p.status, PlanStatusChoices.DONT_KNOW)
        self.assertEqual(p.snooze_until, None)

    def test_answer_unsets_snooze_until(self):
        now = datetime.now(tz=timezone.get_current_timezone())
        _, _, p = self.assoc_joe_and_create_gig()
        p.status = PlanStatusChoices.DONT_KNOW
        p.snooze_until = now
        p.save()

        p.status = PlanStatusChoices.DEFINITELY
        p.save()
        p.refresh_from_db()
        self.assertEqual(p.snooze_until, None)

    # tests of date/time setting using the form
    def assertDateEqual(self, d1, d2):
        """compare dates ignoring timezone"""
        for a in ["month", "day", "year", "hour", "minute"]:
            self.assertEqual(getattr(d1, a), getattr(d2, a))

    def test_no_date_time(self):
        # should fail and reload the edit page - response code 200
        _, _, _ = self.assoc_joe_and_create_gig(
            call_date="", call_time="", expect_code=200
        )

    def test_date_only(self):
        g, _, _ = self.assoc_joe_and_create_gig(call_date="01/02/2023", call_time="")
        self.assertDateEqual(
            g.date, datetime(month=1, day=2, year=2023, hour=0, minute=0)
        )

    def test_dates_only(self):
        g, _, _ = self.assoc_joe_and_create_gig(
            call_date="01/02/2023", call_time="", end_date="02/03/2023"
        )
        self.assertDateEqual(
            g.date, datetime(month=1, day=2, year=2023, hour=0, minute=0)
        )
        self.assertIsNone(g.setdate)
        self.assertDateEqual(
            g.enddate, datetime(month=2, day=3, year=2023, hour=0, minute=0)
        )

    def test_times(self):
        g, _, _ = self.assoc_joe_and_create_gig(
            call_date="01/02/2023",
            call_time="12:00 pm",
            set_time="1:00 pm",
            end_time="2:00 pm",
        )
        self.assertDateEqual(
            g.date, datetime(month=1, day=2, year=2023, hour=12, minute=0)
        )
        self.assertDateEqual(
            g.setdate, datetime(month=1, day=2, year=2023, hour=13, minute=0)
        )
        self.assertDateEqual(
            g.enddate, datetime(month=1, day=2, year=2023, hour=14, minute=0)
        )

    def test_settime_order(self):
        # should fail and reload the edit page - response code 200
        _, _, _ = self.assoc_joe_and_create_gig(
            call_date="01/02/2023",
            call_time="1:00 pm",
            set_time="12:00 pm",
            expect_code=200,
        )

    def test_endtime_order(self):
        # should fail and reload the edit page - response code 200
        _, _, _ = self.assoc_joe_and_create_gig(
            call_date="01/02/2023",
            call_time="1:00 pm",
            end_time="12:00 pm",
            expect_code=200,
        )

    # testing gig comments
    def send_comment(self, user, gig, text):
        c = Client()
        c.force_login(user)
        response = c.post(f"/gig/{gig.id}/comments", {"commenttext": text})
        return response

    def test_gig_comment(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        self.assertEqual(GigComment.objects.count(), 0)
        self.send_comment(self.joeuser, g, "test")
        self.assertEqual(GigComment.objects.count(), 1)

    def test_blank_gig_comment(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        self.assertEqual(GigComment.objects.count(), 0)
        self.send_comment(self.joeuser, g, "")
        self.assertEqual(GigComment.objects.count(), 0)

    def test_gig_make_comment_permissions(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        response = self.send_comment(self.janeuser, g, "illegal!")
        self.assertEqual(GigComment.objects.count(), 0)
        self.assertEqual(response.status_code, 403)

    def test_gig_get_comments(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        c = Client()
        c.force_login(self.joeuser)
        response = c.get(f"/gig/{g.id}/comments")
        self.assertEqual(response.status_code, 200)

    def test_gig_get_comments_permissions(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        c = Client()
        c.force_login(self.janeuser)
        response = c.get(f"/gig/{g.id}/comments")
        self.assertEqual(response.status_code, 403)

    def duplicate_gig_form(
        self,
        gig,
        number=1,
        user=None,
        expect_code=302,
        call_date="01/02/2100",
        end_date="",
        call_time="12:00 pm",
        set_time="",
        end_time="",
        **kwargs,
    ):

        c = Client()
        c.force_login(user if user else self.joeuser)
        response = c.post(
            f"/gig/{gig.id}/duplicate",
            {
                "title": f"Copy of {gig.title}",
                "call_date": call_date,
                "end_date": end_date,
                "call_time": call_time,
                "set_time": set_time,
                "end_time": end_time,
                "contact": kwargs.get("contact", self.joeuser).id,
                "status": GigStatusChoices.UNKNOWN,
                "send_update": True,
            },
        )

        self.assertEqual(
            response.status_code, expect_code
        )  # should get a redirect to the gig info page
        obj = Gig.objects.last()
        return obj

    def test_duplicate_gig(self):
        g1, _, _ = self.assoc_joe_and_create_gig()
        self.assertEqual(Gig.objects.count(), 1)

        _ = self.duplicate_gig_form(
            g1, 1, user=self.joeuser, expect_code=403
        )  # should fail
        self.assertEqual(Gig.objects.count(), 1)

        _ = self.duplicate_gig_form(g1, 1, user=self.band_admin)
        self.assertEqual(Gig.objects.count(), 2)

    def test_address_url(self):
        g, _, _ = self.assoc_joe_and_create_gig(address="http://pbs.org")
        c = Client()
        c.force_login(self.joeuser)
        response = c.get(f"/gig/{g.id}/")
        self.assertIn('"http://pbs.org"', response.content.decode("ascii"))

    def test_address_url_noscheme(self):
        g, _, _ = self.assoc_joe_and_create_gig(address="pbs.org")
        c = Client()
        c.force_login(self.joeuser)
        response = c.get(f"/gig/{g.id}/")
        self.assertIn('"http://pbs.org"', response.content.decode("ascii"))

    def test_address_address(self):
        g, _, _ = self.assoc_joe_and_create_gig(address="1600 Pennsylvania Avenue")
        c = Client()
        c.force_login(self.joeuser)
        response = c.get(f"/gig/{g.id}/")
        self.assertIn(
            '"http://maps.google.com?q=1600 Pennsylvania Avenue"',
            response.content.decode("ascii"),
        )

    # Use plan-update to test permissions
    def test_plan_update_user(self):
        _, _, p = self.assoc_joe_and_create_gig()
        self.client.force_login(self.joeuser)
        resp = self.client.post(
            reverse("plan-update", args=[p.id, PlanStatusChoices.DEFINITELY])
        )
        self.assertEqual(resp.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.status, PlanStatusChoices.DEFINITELY)

    def test_plan_update_admin(self):
        _, _, p = self.assoc_joe_and_create_gig()
        self.client.force_login(self.band_admin)
        resp = self.client.post(
            reverse("plan-update", args=[p.id, PlanStatusChoices.DEFINITELY])
        )
        self.assertEqual(resp.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.status, PlanStatusChoices.DEFINITELY)

    def test_plan_update_other(self):
        _, _, p = self.assoc_joe_and_create_gig()
        self.client.force_login(self.janeuser)
        resp = self.client.post(
            reverse("plan-update", args=[p.id, PlanStatusChoices.DEFINITELY])
        )
        self.assertEqual(resp.status_code, 403)
        p.refresh_from_db()
        self.assertEqual(p.status, PlanStatusChoices.NO_PLAN)

    def test_plan_feedback_user(self):
        _, _, p = self.assoc_joe_and_create_gig()
        self.client.force_login(self.joeuser)
        resp = self.client.post(reverse("plan-update-feedback", args=[p.id, 42]))
        self.assertEqual(resp.status_code, 204)
        p.refresh_from_db()
        self.assertEqual(p.feedback_value, 42)

    def test_plan_comment_user(self):
        _, _, p = self.assoc_joe_and_create_gig()
        self.client.force_login(self.joeuser)
        resp = self.client.post(
            reverse("plan-update-comment", args=[p.id]), {"value": "Plan comment"}
        )
        self.assertEqual(resp.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.comment, "Plan comment")

    def test_plan_section_user(self):
        _, _, p = self.assoc_joe_and_create_gig()
        s = Section.objects.create(name="s1", band=self.band)
        self.client.force_login(self.joeuser)
        resp = self.client.post(reverse("plan-update-section", args=[p.id, s.id]))
        self.assertEqual(resp.status_code, 204)
        p.refresh_from_db()
        self.assertEqual(p.plan_section, s)

    def test_gig_trash(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        self.client.force_login(self.joeuser)
        resp = self.client.post(reverse("gig-trash", args=[g.id]))
        # should fail - joeuser is not an admin
        self.assertEqual(resp.status_code, 403)
        self.client.force_login(self.band_admin)
        resp = self.client.post(reverse("gig-trash", args=[g.id]))
        self.assertEqual(resp.status_code, 302)  # should redirect

    def test_gig_autoarchive(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        self.assertFalse(g.is_archived)
        archive_old_gigs()
        g.refresh_from_db()
        self.assertFalse(g.is_archived)
        g.date = timezone.datetime(2000, 1, 2, 12, tzinfo=pytz_timezone("UTC"))
        g.save()
        archive_old_gigs()
        g.refresh_from_db()
        self.assertTrue(g.is_archived)


class GigSecurityTest(GigTestBase):
    def test_gig_detail_access(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        c = Client()
        c.force_login(self.joeuser)
        response = c.get(reverse("gig-detail", args=[g.id]))
        self.assertEqual(response.status_code, 200)

        c.force_login(self.janeuser)
        response = c.get(reverse("gig-detail", args=[g.id]))
        self.assertEqual(response.status_code, 403)  # fail if we're not associated

        c = Client()
        response = c.get(reverse("gig-detail", args=[g.id]))
        self.assertEqual(response.status_code, 302)  # fail if we're logged out

    def test_gig_create_access(self):
        _, _, _ = self.assoc_joe_and_create_gig()
        c = Client()
        c.force_login(self.joeuser)
        response = c.get(reverse("gig-create", args=[self.band.id]))
        self.assertEqual(response.status_code, 200)

        c.force_login(self.janeuser)
        response = c.get(reverse("gig-create", args=[self.band.id]))
        self.assertEqual(response.status_code, 403)  # fail if we're not associated

        self.assoc_user(self.janeuser)
        response = c.get(reverse("gig-create", args=[self.band.id]))
        self.assertEqual(response.status_code, 200)  # pass - we're assoc'd
        self.band.anyone_can_create_gigs = False
        self.band.save()
        response = c.get(reverse("gig-create", args=[self.band.id]))
        self.assertEqual(response.status_code, 403)  # fail if we can't create gigs

        c = Client()
        response = c.get(reverse("gig-detail", args=[self.band.id]))
        self.assertEqual(response.status_code, 302)  # fail if we're logged out

    def test_gig_edit_access(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        c = Client()
        c.force_login(self.joeuser)
        response = c.get(reverse("gig-update", args=[g.id]))
        self.assertEqual(response.status_code, 200)

        c.force_login(self.janeuser)
        response = c.get(reverse("gig-update", args=[g.id]))
        self.assertEqual(response.status_code, 403)  # fail if we're not associated

        self.assoc_user(self.janeuser)
        response = c.get(reverse("gig-update", args=[g.id]))
        self.assertEqual(response.status_code, 200)  # pass - we're assoc'd
        self.band.anyone_can_manage_gigs = False
        self.band.save()
        response = c.get(reverse("gig-update", args=[g.id]))
        self.assertEqual(response.status_code, 403)  # fail if we can't create gigs

        c = Client()
        response = c.get(reverse("gig-update", args=[g.id]))
        self.assertEqual(response.status_code, 302)  # fail if we're logged out
