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
from django.core import mail
from django.test import TestCase, Client
from member.models import Member
from band.models import Band, Section, Assoc
from band.util import AssocStatusChoices
from gig.util import GigStatusChoices, PlanStatusChoices
from .models import Gig, Plan, GigComment
from .helpers import send_reminder_email, create_gig_series
from .tasks import send_snooze_reminders
from .tasks import archive_old_gigs
from datetime import timedelta, datetime, timezone as dttimezone
from django.urls import reverse
from django.utils import timezone
from pytz import utc, timezone as pytimezone
from lib.template_test import MISSING, flag_missing_vars
from freezegun import freeze_time

# workaround for freezegun thing where it ignores modules with names
# that start with "gi" for some reason
from freezegun.config import DEFAULT_IGNORE_LIST, configure
configure([x for x in DEFAULT_IGNORE_LIST if not x == 'gi'])


class GigTestBase(TestCase):
    def setUp(self):
        self.super = Member.objects.create_user(
            email="super@b.c", is_superuser=True)
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
        """ make sure we get rid of anything we made """
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
            datetime(2100, 1, 2, 12, tzinfo=pytimezone("US/Eastern"))
            if start_date == "auto"
            else start_date
        )
        return Gig.objects.create(
            title=title,
            band_id=self.band.id,
            date=thedate,
            setdate=thedate +
            timedelta(minutes=30) if set_date == "auto" else set_date,
            enddate=thedate +
            timedelta(hours=2) if end_date == "auto" else end_date,
            contact=the_member,
            status=GigStatusChoices.UNCONFIRMED,
            email_changes=True,
        )

    def create_one_gig_of_each_status(self):
        self.create_gig_form(contact=self.joeuser, title=f"Unconfirmed Gig-xyzzy", status=GigStatusChoices.UNCONFIRMED)
        self.create_gig_form(contact=self.joeuser, title=f"Canceled Gig-xyzzy", status=GigStatusChoices.CANCELED)
        self.create_gig_form(contact=self.joeuser, title=f"Confirmed Gig-xyzzy", status=GigStatusChoices.CONFIRMED)
        self.create_gig_form(contact=self.joeuser, title=f"Asking Gig-xyzzy", status=GigStatusChoices.ASKING)

    def create_gig_form(
        self,
        user=None,
        expect_code=302,
        is_full_day=False,
        call_date="01/02/2100",
        set_date="",
        end_date="",
        call_time="12:00 pm",
        set_time="",
        end_time="",
        title="New Gig",
        email_changes=True,
        **kwargs,
    ):

        status = kwargs.pop("status", GigStatusChoices.UNCONFIRMED)
        contact = kwargs.pop("contact", self.joeuser).id
        send_update = kwargs.pop("send_update", True)
        the_band = kwargs.pop("band",self.band)

        c = Client()
        c.force_login(user if user else self.joeuser)
        response = c.post(
            f"/gig/create/{the_band.id}",
            {
                "title": title,
                "is_full_day": is_full_day,
                "call_date": call_date,
                "call_time": call_time,
                "set_date": set_date,
                "set_time": set_time,
                "end_date": end_date,
                "end_time": end_time,
                "contact": contact,
                "status": status,
                "send_update": send_update,
                "email_changes": email_changes,
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

    def update_gig_form(self, the_gig,  user=None, expect_code=302, **kwargs):

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
            "email_changes": True,
        }
        for x in kwargs.keys():
            data[x] = kwargs[x]

        c = Client()
        c.force_login(user if user else self.joeuser)
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

    def add_members(self,num,band=None):
        c = Member.objects.count()
        members = []
        assocs = []
        if band is None:
            band = self.band
        for i in range(c,num+c):
            m = Member.objects.create_user(email=f'member{i}@b.c')
            members.append(m)
            a = Assoc.objects.create(member=m, band=band, status=AssocStatusChoices.CONFIRMED)
            assocs.append(a)
        return members, assocs

class GigTest(GigTestBase):
    def test_no_section(self):
        """ show that the band has a default section called 'No Section' """
        self.assoc_user(self.joeuser)
        a = self.band.assocs.first()
        s = a.default_section
        self.assertTrue(s.is_default)
        self.assertTrue(s.name, "No Section")

    def test_gig_plans(self):
        """ show that when a gig is created, every member has a plan """
        self.assoc_user(self.joeuser)
        g = self.create_gig_form()
        self.assertEqual(g.plans.count(), self.band.assocs.count())

    def test_plan_section(self):
        """ show that when we have a gig plan, it uses the default section """
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
        """ show that if we delete a section which has been selected as a plan override
        that the plan section is set back to the user's default section, not the
        band's default section """

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
        self.assertEqual(p.section, s2) # should be using the override

        # now delete the override section
        s2.delete()
        p.refresh_from_db()
        self.assertEqual(p.section, s1) # should revert to joe's default


    def test_gig_create_permissions(self):
        """ make sure that if I don't have permission to create a gig, I can't """
        self.band.anyone_can_create_gigs = False
        self.band.save()
        # need a member of the band so there's a valid contact to select from in the form
        self.assoc_user(self.joeuser)
        self.create_gig_form(
            user=self.janeuser, title="permission gig", expect_code=403
        )

        # now make sure I can!
        self.band.anyone_can_create_gigs = True
        self.band.save()
        # need a member of the band so there's a valid contact to select from in the form
        self.create_gig_form(
            user=self.joeuser, title="permission gig", expect_code=302
        )


    def test_gig_edit_permissions(self):
        """ make sure that if I don't have permission to edit a gig, I can't """
        g, a, _ = self.assoc_joe_and_create_gig(
            set_time="12:30 pm", end_time="02:00 pm"
        )
        self.band.anyone_can_manage_gigs = False
        self.band.save()

        # not in band
        self.update_gig_form(g, user=self.janeuser,
                             title="not legal!", expect_code=403)

        # not in band
        self.band.anyone_can_manage_gigs = True
        self.band.save()
        self.update_gig_form(g, user=self.janeuser,
                             title="not legal!", expect_code=403)

        # in band but not admin, but anyone can edit so it's cool
        a.is_admin = False
        a.save()
        self.update_gig_form(g, user=self.joeuser,
                             title="legal!", expect_code=302)


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
            "Call Time: noon\nSet Time: 12:30 p.m.\nEnd Time: 2 p.m.", message.body
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

    def test_gig_creator_set(self):
        g,_,_ = self.assoc_joe_and_create_gig(set_time="", end_time="02:00 pm")
        self.assertEqual(g.creator, self.joeuser)


    def test_gig_time_no_set(self):
        self.assoc_joe_and_create_gig(set_time="", end_time="02:00 pm")
        self.assertIn(
            "End Time: 2 p.m.", mail.outbox[0].body
        )

    def test_gig_time_no_end(self):
        self.assoc_joe_and_create_gig(
            set_time="12:30 pm", end_date="", end_time="")
        self.assertIn(
            "Set Time: 12:30 p.m.",
            mail.outbox[0].body,
        )

    def test_gig_occasionals(self):
        a = self.band.all_assocs
        self.assertEqual(len(a),1)
        super_a = a[0]
        super_a.email_me = True
        super_a.save()
        joe_a = self.assoc_user(self.joeuser)
        joe_a.is_occasional = False
        joe_a.save()
        self.create_gig_form(contact=self.joeuser, email_changes = True, invite_occasionals=True)
        self.assertEqual(len(mail.outbox),2)  # both should get email
        joe_a.is_occasional = True
        joe_a.save()
        mail.outbox.clear()
        self.create_gig_form(contact=self.joeuser, email_changes = True, invite_occasionals=True)
        self.assertEqual(len(mail.outbox),2) # both should get email
        mail.outbox.clear()
        self.create_gig_form(contact=self.joeuser, email_changes = True, invite_occasionals=False)
        self.assertEqual(len(mail.outbox),1) # only superuser gets email
        mail.outbox.clear()
        self.create_gig_form(contact=self.joeuser, email_changes = False, invite_occasionals=True)
        self.assertEqual(len(mail.outbox),0) # nobody gets email

    def test_hide_gig_for_user(self):
        a = self.band.all_assocs
        self.assertEqual(len(a),1)
        super_a = a[0]
        self.assertTrue(super_a.is_admin)
        super_a.email_me = True
        super_a.save()
        joe_a = self.assoc_user(self.joeuser)
        joe_a.hide_from_schedule = False
        joe_a.save()
        self.create_gig_form(contact=self.band_admin, email_changes = True, invite_occasionals=True)
        plans = self.joeuser.calendar_plans
        self.assertEqual(len(plans),1)  # should see the gig in the calendar_plans
        joe_a.hide_from_schedule = True
        joe_a.save()
        plans = self.joeuser.calendar_plans
        self.assertEqual(len(plans),0)  # should not see the gig in the calendar_plans

    def test_gig_time_no_set_no_end(self):
        self.assoc_joe_and_create_gig(set_time="", end_date="", end_time="")
        self.assertIn("Call Time: noon", mail.outbox[0].body)

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
        self.assertIn(
            "Beginn: 12:00\nTermin: 12:30\nEnde: 14:00", message.body)
        self.assertIn("Nicht fixiert", message.body)


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
            snooze_until=timezone.localtime(timezone=dttimezone.utc)
        )
        mail.outbox = []
        send_snooze_reminders()

        self.assertEqual(len(mail.outbox), 2)
        for message in mail.outbox:
            self.assertIn("Reminder", message.subject)
        self.assertEqual(g.member_plans.filter(
            snooze_until__isnull=False).count(), 0)

    def test_snooze_until_cutoff(self):
        joeassoc = Assoc.objects.create(
            member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED
        )
        janeassoc = Assoc.objects.create(
            member=self.janeuser, band=self.band, status=AssocStatusChoices.CONFIRMED
        )
        g = self.create_gig_form()
        now = timezone.localtime(timezone=dttimezone.utc)
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
        now = timezone.localtime(timezone=dttimezone.utc)
        g.member_plans.filter(assoc=a).update(snooze_until=now+timedelta(days=2))
        mail.outbox = []
        send_snooze_reminders()
        self.assertEqual(len(mail.outbox), 0)

        g.member_plans.filter(assoc=a).update(snooze_until=now)
        mail.outbox = []
        send_snooze_reminders()
        self.assertEqual(len(mail.outbox), 1)

        # do it again to make sure we don't send again
        mail.outbox = []
        send_snooze_reminders()
        self.assertEqual(len(mail.outbox), 0)


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
        self.assertIn("(Date/Time)", message.subject)
        self.assertIn("Call Time: 2 p.m.", message.body)

    def test_gig_edit_add_time(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        self.update_gig_form(g)

        mail.outbox = []
        settime = g.date + timedelta(hours=2)
        self.update_gig_form(
            g, set_date=self._dateformat(settime), set_time=self._timeformat(settime)
        )

        message = mail.outbox[0]
        self.assertIn("(Date/Time)", message.subject)
        self.assertIn("Call Time: noon\nSet Time: 2 p.m.", message.body)

    def test_gig_edit_contact(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        mail.outbox = []
        # Jane needs to be in the band to be a contact for this gig
        self.assoc_user(self.janeuser)
        self.update_gig_form(g, contact=self.janeuser.id)

        message = mail.outbox[0]
        self.assertIn("Contact", message.subject)
        self.assertIn(self.janeuser.display_name, message.body)
        self.assertIn(f"(was {self.joeuser.display_name})", message.body)

    def test_gig_edit_setlist(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        self.update_gig_form(g)

        mail.outbox = []
        self.update_gig_form(
            g, setlist="Tequila\nLand of a Thousand Dances"
        )

        message = mail.outbox[0]
        self.assertIn("(Set List)", message.subject)

    def test_gig_edit_address(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        self.update_gig_form(g)

        mail.outbox = []
        self.update_gig_form(
            g, address="123 Main St. Anytown, MN 55016"
        )

        message = mail.outbox[0]
        self.assertIn("(Address)", message.subject)
        self.assertIn("Address: 123 Main St. Anytown, MN 55016", message.body)

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
        self.assertIn("(Datum/Uhrzeit)", message.subject)

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
        now = timezone.now().replace(tzinfo=None)
        _, _, p = self.assoc_joe_and_create_gig()
        response = self.client.get(
            reverse("gig-answer", args=[p.id, PlanStatusChoices.DONT_KNOW])
        )
        p.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(p.status, PlanStatusChoices.DONT_KNOW)
        self.assertGreaterEqual((p.snooze_until.date() - now.date()).days, 7)

    def test_answer_snooze_short(self):
        now = timezone.now().replace(tzinfo=None)
        g, _, p = self.assoc_joe_and_create_gig()
        g.date = now.date() + timedelta(days=3)
        response = self.client.get(
            reverse("gig-answer", args=[p.id, PlanStatusChoices.DONT_KNOW])
        )
        p.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(p.status, PlanStatusChoices.DONT_KNOW)
        self.assertLessEqual((p.snooze_until.date() - now.date()).days, 7)

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
        now = timezone.localtime(timezone=dttimezone.utc)
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
        """ compare dates ignoring timezone """
        for a in ["month", "day", "year", "hour", "minute"]:
            self.assertEqual(getattr(d1, a), getattr(d2, a))

    def test_no_date_time(self):
        # should fail and reload the edit page - response code 200
        _, _, _ = self.assoc_joe_and_create_gig(
            call_date="", call_time="", expect_code=200
        )

    def test_date_only(self):
        future_date = timezone.now() + timedelta(days=7)
        g, _, _ = self.assoc_joe_and_create_gig(
            call_date=future_date.strftime("%m/%d/%Y"), call_time="")
        self.assertDateEqual(
            g.date, datetime(month=future_date.month, day=future_date.day, year=future_date.year, hour=0, minute=0)
        )

    def test_dates_only(self):
        future_start_date = timezone.now() + timedelta(days=7)
        future_end_date = future_start_date + timedelta(days=1)
        g, _, _ = self.assoc_joe_and_create_gig(
            call_date=future_start_date.strftime("%m/%d/%Y"), call_time="", end_date=future_end_date.strftime("%m/%d/%Y")
        )
        self.assertDateEqual(
            g.date, datetime(month=future_start_date.month, day=future_start_date.day, year=future_start_date.year, hour=0, minute=0)
        )
        self.assertIsNone(g.setdate)
        self.assertIsNone(g.enddate)

    def test_times(self):
        future_date = timezone.now() + timedelta(days=7)
        g, _, _ = self.assoc_joe_and_create_gig(
            call_date=future_date.strftime("%m/%d/%Y"),
            call_time="12:00 pm",
            set_time="1:00 pm",
            end_time="2:00 pm",
        )
        self.assertDateEqual(
            g.date, datetime(month=future_date.month, day=future_date.day, year=future_date.year, hour=12, minute=0)
        )
        self.assertDateEqual(
            g.setdate, datetime(month=future_date.month, day=future_date.day, year=future_date.year, hour=13, minute=0)
        )
        self.assertDateEqual(
            g.enddate, datetime(month=future_date.month, day=future_date.day, year=future_date.year, hour=14, minute=0)
        )

    def test_settime_order(self):
        future_date = timezone.now() + timedelta(days=7)
        # because set time is before call time,
        # this should fail and reload the edit page - response code 200
        _, _, _ = self.assoc_joe_and_create_gig(
            call_date=future_date.strftime("%m/%d/%Y"),
            call_time="1:00 pm",
            set_time="12:00 pm",
            expect_code=200,
        )

    def test_endtime_order(self):
        future_date = timezone.now() + timedelta(days=7)
        # because end time is before call time,
        # should fail and reload the edit page - response code 200
        _, _, _ = self.assoc_joe_and_create_gig(
            call_date=future_date.strftime("%m/%d/%Y"),
            call_time="1:00 pm",
            end_time="12:00 pm",
            expect_code=200,
        )

    def test_gig_date_in_past(self):
        past_date = timezone.now() - timedelta(days=7)
        # because gig date is in the past,
        # should fail and reload the edit page - response code 200
        _, _, _ = self.assoc_joe_and_create_gig(
            call_date=past_date.strftime("%m/%d/%Y"),
            call_time="1:00 pm",
            end_time="2:00 pm",
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
                "status": GigStatusChoices.UNCONFIRMED,
                "send_update": True,
            },
        )

        self.assertEqual(
            response.status_code, expect_code
        )  # should get a redirect to the gig info page
        obj = Gig.objects.last()
        return obj

    def test_duplicate_gig(self):
        self.band.anyone_can_create_gigs = False
        self.band.save()

        g1, _, _ = self.assoc_joe_and_create_gig(user=self.band_admin)
        self.assertEqual(Gig.objects.count(), 1)

        _ = self.duplicate_gig_form(
            g1, 1, user=self.joeuser, expect_code=403
        )  # should fail
        self.assertEqual(Gig.objects.count(), 1)

        _ = self.duplicate_gig_form(g1, 1, user=self.band_admin)
        self.assertEqual(Gig.objects.count(), 2)

    def test_series_of_simple_gigs(self):
        g1, _, _ = self.assoc_joe_and_create_gig()
        self.assertEqual(Gig.objects.count(), 1)

        create_gig_series(g1, 2, "day")
        self.assertEqual(Gig.objects.count(), 2)

        gigs = list(Gig.objects.all())
        gigs.sort(key=lambda x: x.date)

        g1 = gigs[0]
        g2 = gigs[1]
        self.assertEqual(g2.date - g1.date, timedelta(days=1))

    def test_series_email(self):
        self.assoc_user(self.joeuser)
        self.band.anyone_can_create_gigs = True
        self.band.save()
        g=self.create_gig_form(add_series=True,
                             total_gigs=3,
                             repeat='day',
                             )
        self.assertEqual(len(mail.outbox),1)
        message = mail.outbox[0]
        self.assertIn('Series', message.subject)
        self.assertIn(f'Last Date: {g.date.strftime("%m/%d/%Y")}', message.body)


    def test_series_of_full_day_gigs(self):
        g1, _, _ = self.assoc_joe_and_create_gig()
        self.assertEqual(Gig.objects.count(), 1)
        g1.is_full_day = True
        g1.enddate = g1.date + timedelta(days=1)
        g1.save()

        create_gig_series(g1, 2, "week")
        self.assertEqual(Gig.objects.count(), 2)

        gigs = list(Gig.objects.all())
        gigs.sort(key=lambda x: x.date)

        g1 = gigs[0]
        g2 = gigs[1]
        self.assertEqual(g2.date - g1.date, timedelta(days=7))
        self.assertEqual(g2.enddate - g1.enddate, timedelta(days=7))

    def test_series_of_time_gigs(self):
        g1, _, _ = self.assoc_joe_and_create_gig()
        self.assertEqual(Gig.objects.count(), 1)
        g1.is_full_day = False
        g1.setdate = g1.date + timedelta(hours=1)
        g1.enddate = g1.date + timedelta(hours=2)
        g1.has_call_time = True
        g1.has_set_time = True
        g1.has_end_time = True
        g1.save()

        create_gig_series(g1, 3, "week")
        self.assertEqual(Gig.objects.count(), 3)

        gigs = list(Gig.objects.all())
        gigs.sort(key=lambda x: x.date)

        g1 = gigs[0]
        g2 = gigs[1]
        g3 = gigs[2]
        self.assertEqual(g2.date - g1.date, timedelta(days=7))
        self.assertEqual(g2.setdate - g1.setdate, timedelta(days=7))
        self.assertEqual(g2.enddate - g1.enddate, timedelta(days=7))
        self.assertEqual(g3.date - g2.date, timedelta(days=7))
        self.assertEqual(g3.setdate - g2.setdate, timedelta(days=7))
        self.assertEqual(g3.enddate - g2.enddate, timedelta(days=7))

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
        g, _, _ = self.assoc_joe_and_create_gig(
            address="1600 Pennsylvania Avenue")
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
        resp = self.client.post(
            reverse("plan-update-feedback", args=[p.id, 42]))
        self.assertEqual(resp.status_code, 204)
        p.refresh_from_db()
        self.assertEqual(p.feedback_value, 42)

    def test_plan_comment_user(self):
        _, _, p = self.assoc_joe_and_create_gig()
        self.client.force_login(self.joeuser)
        resp = self.client.post(
            reverse("plan-update-comment",
                    args=[p.id]), {"value": "Plan comment"}
        )
        self.assertEqual(resp.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.comment, "Plan comment")

    def test_long_plan_comment_user(self):
        _, _, p = self.assoc_joe_and_create_gig()
        self.client.force_login(self.joeuser)
        resp = self.client.post(
            reverse("plan-update-comment",
                    args=[p.id]), {"value": "123456789 123456789 123456789 123456789 123456789 123456789 123456789 123456789 \
                                   123456789 123456789 123456789 123456789 123456789 123456789 123456789 123456789 123456789 \
                                   123456789 123456789 123456789 xxxxxxxxx"}  # 210 characters
        )
        self.assertEqual(resp.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(len(p.comment), 200)

    def test_plan_section_user(self):
        _, _, p = self.assoc_joe_and_create_gig()
        s = Section.objects.create(name="s1", band=self.band)
        self.client.force_login(self.joeuser)
        resp = self.client.post(
            reverse("plan-update-section", args=[p.id, s.id]))
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

    def test_gig_shown(self):
        """
            assure that a gig that happened in the past day still shows up as a 'future plan'
            so it's on the schedule page
        """
        import pytz

        g, _, _ = self.assoc_joe_and_create_gig()
        self.joeuser.preferences.current_timezone='America/New_York'
        self.joeuser.save()

        timezone.activate(self.joeuser.preferences.current_timezone)

        # make the gig date noon on 4/1/24 in New York
        g.date = datetime(year=2024, month=4, day=1, hour=12, minute=0, tzinfo=timezone.get_current_timezone())
        g.save()

        # first, pretend it's the day before the gig
        with freeze_time(g.date - timedelta(days=1)):
            gigs = [p.gig for p in Plan.member_plans.future_plans(self.joeuser)]
        self.assertTrue(g in gigs)

        # now pretend it's the time of the gig
        with freeze_time(g.date):
            gigs = [p.gig for p in Plan.member_plans.future_plans(self.joeuser)]
        self.assertTrue(g in gigs)

        # now pretend it's almost 4 hours later
        with freeze_time(g.date + timedelta(hours=3,minutes=50)):
            gigs = [p.gig for p in Plan.member_plans.future_plans(self.joeuser)]
        self.assertTrue(g in gigs)

        # now pretend it's more than 4 hours later
        with freeze_time(g.date + timedelta(hours=4,minutes=10)):
            gigs = [p.gig for p in Plan.member_plans.future_plans(self.joeuser)]
        self.assertFalse(g in gigs)


    def test_gig_autoarchive(self):

        def _check_gig(g,is_full_day,date,setdate,enddate):
            g.is_archived = False
            g.is_full_day = is_full_day
            g.date = date
            g.startdate = setdate
            g.enddate = enddate
            g.save()
            archive_old_gigs()
            g.refresh_from_db()
            return g.is_archived

        g, _, _ = self.assoc_joe_and_create_gig()

        # test an all-day gig with no end date
        self.assertFalse(_check_gig(g, True, timezone.now(), None, None))
        self.assertTrue(_check_gig(g, True, timezone.now()-timedelta(days=10), None, None))

        # test an all-day gig with an end date
        self.assertFalse(_check_gig(g, True, timezone.now()-timedelta(days=11), None, timezone.now()))
        self.assertTrue(_check_gig(g, True, timezone.now()-timedelta(days=11), None, timezone.now()-timedelta(days=10)))

        # test non-all-day gig with no end date
        self.assertFalse(_check_gig(g, False, timezone.now(), None, None))
        self.assertTrue(_check_gig(g, False, timezone.now()-timedelta(days=10), None, None))

    def test_gig_default_call_date_to_set_date(self):
        future_date = timezone.now() + timedelta(days=7)
        g, _, _ = self.assoc_joe_and_create_gig(
            call_date=future_date.strftime("%m/%d/%Y"), call_time="",
            set_date=future_date.strftime("%m/%d/%Y"), set_time="1:00 pm",
            is_full_day=False,
        )
        self.assertEqual(g.date, g.setdate)
        self.assertEqual(g.has_call_time, True)

    def test_gig_default_full_day_without_times(self):
        future_date = timezone.now() + timedelta(days=7)
        g, _, _ = self.assoc_joe_and_create_gig(
            call_date=future_date.strftime("%m/%d/%Y"), call_time="",
            set_date=future_date.strftime("%m/%d/%Y"), set_time="",
            is_full_day=False,
        )
        self.assertEqual(g.is_full_day, True)

    def test_gig_zones(self):
        self.band.timezone="US/Eastern"
        self.band.save()
        g, a, _= self.assoc_joe_and_create_gig(
            is_full_day=True,
            call_date="2/1/2030"
        )
        self.assertEqual(g.date.day,1)

        a.delete()

        g, _, _= self.assoc_joe_and_create_gig(
            is_full_day=True,
            call_date="2/1/2030",
            end_date="2/2/2030"
        )
        self.assertEqual(g.date.day,1)
        self.assertEqual(g.enddate.day,2)


class GigSecurityTest(GigTestBase):
    def test_gig_detail_access(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        c = Client()
        c.force_login(self.joeuser)
        response = c.get(reverse("gig-detail", args=[g.id]))
        self.assertEqual(response.status_code, 200)

        c.force_login(self.janeuser)
        response = c.get(reverse("gig-detail", args=[g.id]))
        self.assertEqual(response.status_code, 403) # fail if we're not associated

        c = Client()
        response = c.get(reverse("gig-detail", args=[g.id]))
        self.assertEqual(response.status_code, 302) # fail if we're logged out

    def test_gig_create_access(self):
        _, _, _ = self.assoc_joe_and_create_gig()
        c = Client()
        c.force_login(self.joeuser)
        response = c.get(reverse("gig-create", args=[self.band.id]))
        self.assertEqual(response.status_code, 200)

        c.force_login(self.janeuser)
        response = c.get(reverse("gig-create", args=[self.band.id]))
        self.assertEqual(response.status_code, 403) # fail if we're not associated

        self.assoc_user(self.janeuser)
        response = c.get(reverse("gig-create", args=[self.band.id]))
        self.assertEqual(response.status_code, 200) # pass - we're assoc'd
        self.band.anyone_can_create_gigs = False
        self.band.save()
        response = c.get(reverse("gig-create", args=[self.band.id]))
        self.assertEqual(response.status_code, 403) # fail if we can't create gigs

        c = Client()
        response = c.get(reverse("gig-create", args=[self.band.id]))
        self.assertEqual(response.status_code, 302) # fail if we're logged out

    def test_gig_edit_access(self):
        g, _, _ = self.assoc_joe_and_create_gig()
        c = Client()
        c.force_login(self.joeuser)
        response = c.get(reverse("gig-update", args=[g.id]))
        self.assertEqual(response.status_code, 200)

        c.force_login(self.janeuser)
        response = c.get(reverse("gig-update", args=[g.id]))
        self.assertEqual(response.status_code, 403) # fail if we're not associated

        self.assoc_user(self.janeuser)
        response = c.get(reverse("gig-update", args=[g.id]))
        self.assertEqual(response.status_code, 200) # pass - we're assoc'd
        self.band.anyone_can_manage_gigs = False
        self.band.save()
        self.band.refresh_from_db()
        g.band.refresh_from_db()
        response = c.get(reverse("gig-update", args=[g.id]))
        self.assertEqual(response.status_code, 403) # fail if we can't create gigs

        g.creator = self.janeuser
        g.save()
        response = c.get(reverse("gig-update", args=[g.id]))
        self.assertEqual(response.status_code, 200) # pass if we created the gig

        c = Client()
        response = c.get(reverse("gig-update", args=[g.id]))
        self.assertEqual(response.status_code, 302) # fail if we're logged out


class TestGigAPI(GigTestBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.joeuser)
        self.assoc_user(self.joeuser)
        self.create_one_gig_of_each_status()
        self.client.get(reverse("member-generate-api-key"))
        self.joeuser.refresh_from_db()
        self.unconfirmed_member = Member.objects.create_user(email="uncomfirmed@h.i", api_key="unconfirmed")
        Assoc.objects.create(
            member=self.unconfirmed_member, band=self.band, status=AssocStatusChoices.INVITED
        )

    def test_gigs(self):
        response = self.client.get(reverse("api-1.0.0:list_all_gigs"), HTTP_X_API_KEY=self.joeuser.api_key)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("count"), 4)
        # make sure there's one of each status in there
        for status in GigStatusChoices.labels:
            checks = [1 for x in data.get("gigs") if x.get("gig_status") == status ]
            self.assertTrue(sum(checks)==1)

            checks = [1 for x in data.get("gigs") if str(status) in x.get("title")]
            self.assertTrue(sum(checks)==1)

        for gig in data.get("gigs"):
            self.assertEqual(gig.get("band"), self.band.name)
            self.assertEqual(gig.get("contact"), self.joeuser.display_name)
            self.assertEqual(gig.get("plan_status"), PlanStatusChoices.NO_PLAN.label)
            self.assertEqual(Gig.objects.get(id=gig.get("id")).plans.filter(assoc__member=self.joeuser).first().assoc.status, AssocStatusChoices.CONFIRMED)

    def test_gigs_uncomfirmed_member(self):
        response = self.client.get(reverse("api-1.0.0:list_all_gigs"), HTTP_X_API_KEY=self.unconfirmed_member.api_key)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("count"), 0)


    def _gig_filter(self, gig_status, status_label):
        response = self.client.get(reverse("api-1.0.0:list_all_gigs"), HTTP_X_API_KEY=self.joeuser.api_key, data={"gig_status": gig_status})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("count"), 1)
        self.assertEqual(data.get("gigs")[0].get("gig_status"), status_label)
        self.assertEqual(data.get("gigs")[0].get("title"), f"{status_label} Gig-xyzzy")

    def test_gig_status_filter(self):
        for status in GigStatusChoices.choices:
            self._gig_filter(status[0], status[1])

    def test_gig_status_filter_invalid_type(self):
        response = self.client.get(reverse("api-1.0.0:list_all_gigs"), HTTP_X_API_KEY=self.joeuser.api_key, data={"gig_status": "INVALID"})
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertEqual(data.get("message"), "Invalid filter")

    def test_gig_status_filter_invalid_value(self):
        response = self.client.get(reverse("api-1.0.0:list_all_gigs"), HTTP_X_API_KEY=self.joeuser.api_key, data={"gig_status": 999})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("count"), 4)

    def _plan_status_filter(self, plan_status, status_label, expected_count):
        response = self.client.get(reverse("api-1.0.0:list_all_gigs"), HTTP_X_API_KEY=self.joeuser.api_key, data={"plan_status": plan_status})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("count"), expected_count)
        self.assertEqual(data.get("gigs")[0].get("plan_status"), status_label)

    def test_plan_status_filter(self):
        Gig.objects.all().delete()
        for status in PlanStatusChoices.choices:
            gig = self.create_gig(the_member=self.joeuser, title=f"plan_status {status[1]} Gig-xyzzy")
            plan = Plan.objects.get(gig=gig, assoc__member=self.joeuser)
            plan.status = status[0]
            plan.save()
            self._plan_status_filter(status[0], status[1], expected_count=1)

    def test_plan_status_filter_invalid_type(self):
        response = self.client.get(reverse("api-1.0.0:list_all_gigs"), HTTP_X_API_KEY=self.joeuser.api_key, data={"plan_status": "INVALID"})
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertEqual(data.get("message"), "Invalid filter")

    def test_plan_status_filter_invalid_value(self):
        response = self.client.get(reverse("api-1.0.0:list_all_gigs"), HTTP_X_API_KEY=self.joeuser.api_key, data={"plan_status": 999})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("count"), 4)

    def test_get_gig(self):
        gig = self.create_gig(the_member=self.joeuser, title="get_gig test")
        response = self.client.get(reverse("api-1.0.0:get_gig", args=[gig.id]), HTTP_X_API_KEY=self.joeuser.api_key)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("title"), "get_gig test")
        self.assertTrue(Gig.objects.get(id=gig.id).plans.filter(assoc__member=self.joeuser).first().assoc.status, AssocStatusChoices.CONFIRMED)

    def test_gig_uncomfirmed_member(self):
        gig = self.create_gig(the_member=self.unconfirmed_member, title="uncomfirmed member test")
        response = self.client.get(reverse("api-1.0.0:get_gig", args=[gig.id]), HTTP_X_API_KEY=self.unconfirmed_member.api_key)
        self.assertEqual(response.status_code, 404)

    def test_get_gig_not_associated(self):
        new_user = Member.objects.create_user(email="new@a.c", api_key="testkey")
        self.client.force_login(new_user)
        gig = self.create_gig(the_member=self.janeuser, title="no association test")
        response = self.client.get(reverse("api-1.0.0:get_gig", args=[gig.id]), HTTP_X_API_KEY=new_user.api_key)
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data.get("message"), "Not found")

    def test_get_gig_not_found(self):
        response = self.client.get(reverse("api-1.0.0:get_gig", args=[999]), HTTP_X_API_KEY=self.joeuser.api_key)
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data.get("message"), "Not found")

    def test_get_gig_status_choices(self):
        response = self.client.get(reverse("api-1.0.0:gig_status_choices"), HTTP_X_API_KEY=self.joeuser.api_key)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [{"id": status[0], "name": status[1]} for status in GigStatusChoices.choices])

    def test_get_plan_status_choices(self):
        response = self.client.get(reverse("api-1.0.0:plan_status_choices"), HTTP_X_API_KEY=self.joeuser.api_key)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [{"id": status[0], "name": status[1]} for status in PlanStatusChoices.choices])
