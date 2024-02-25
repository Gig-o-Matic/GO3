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

from django.test import TestCase, RequestFactory, Client
from .models import Member, MemberPreferences, Invite, EmailConfirmation
from band.models import Band, Assoc, AssocStatusChoices
from gig.models import Gig, Plan
from gig.util import GigStatusChoices, PlanStatusChoices
from .views import AssocsView, OtherBandsView
from .helpers import prepare_calfeed, calfeed, update_member_calfeed
from .util import MemberStatusChoices
from lib.email import DEFAULT_SUBJECT, prepare_email
from lib.template_test import MISSING, flag_missing_vars, TemplateTestCase
from django.conf import settings
from django.contrib import auth
from django.core import mail
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import resolve, reverse
from django.utils import timezone
from pytz import timezone as pytz_timezone
from datetime import timedelta
from graphene.test import Client as graphQLClient
from go3.schema import schema
from gig.tests import GigTestBase
import pytz
import os
from pyfakefs.fake_filesystem_unittest import TestCase as FSTestCase


class MemberTest(TestCase):
    def setUp(self):
        m = Member.objects.create_user("a@b.com", password="abc")
        b = Band.objects.create(name="test band")
        Assoc.objects.create(band=b, member=m)
        Band.objects.create(name="another band")

    def tearDown(self):
        """make sure we get rid of anything we made"""
        Member.objects.all().delete()
        self.assertEqual(Assoc.objects.all().count(), 0)  # should all be gone!
        Band.objects.all().delete()
        Assoc.objects.all().delete()

    def test_member_bands(self):
        """test some basics of member creation"""
        m = Member.objects.all()
        self.assertEqual(len(m), 1)
        m = m[0]
        self.assertEqual(len(m.assocs.all()), 1)
        b = m.assocs.first().band
        self.assertEqual(b.name, "test band")

    def test_memberassocsview(self):
        m = Member.objects.first()
        request = RequestFactory().get("/member/{}/assocs/".format(m.id))
        view = AssocsView()
        view.setup(request, pk="{}".format(m.id))

        context = view.get_context_data()
        self.assertIn("assocs", context)
        self.assertEqual(len(context["assocs"]), 1)
        self.assertEqual(context["assocs"][0].band.name, "test band")

    def test_member_otherbandsview(self):
        m = Member.objects.first()
        request = RequestFactory().get("/member/{}/otherbands/".format(m.id))
        view = OtherBandsView()
        view.setup(request, pk="{}".format(m.id))

        context = view.get_context_data()
        self.assertIn("bands", context)
        self.assertEqual(len(context["bands"]), 1)
        self.assertEqual(context["bands"][0].name, "another band")


class MemberEmailTest(TestCase):
    def setUp(self):
        self.member = Member.objects.create_user("member@example.com")

        _open = open  # Saves a reference to the builtin, for access after patching

        def template_open(filename, *args, **kw):
            # We adopt the convention that a filename begining with 't:' indicates
            # a template that we want to inject, with the contents of the filename
            # following the 't:'.  But the template mechanism tries to open
            # absolute paths, so we need to look for 't:' anywhere in the filename.
            if isinstance(filename, str) and (i := filename.find("t:")) > -1:
                content = filename[i + 2 :]
                return mock_open(read_data=content).return_value
            return _open(filename, *args, **kw)

        self.patcher = patch("builtins.open", template_open)
        self.patcher.start()

    def tearDown(self):
        Member.objects.all().delete()
        self.patcher.stop()

    def test_markdown_mail(self):
        message = prepare_email(self.member.as_email_recipient(), "t:**Markdown**")
        self.assertIn("**Markdown**", message.body)
        self.assertEqual(len(message.alternatives), 1)
        self.assertEqual(message.alternatives[0][1], "text/html")
        self.assertIn("<strong>Markdown</strong>", message.alternatives[0][0])

    def test_markdown_template(self):
        message = prepare_email(
            self.member.as_email_recipient(), "t:{{ key }}", {"key": "value"}
        )
        self.assertIn("value", message.body)
        self.assertIn("value", message.alternatives[0][0])

    def test_markdown_template_member(self):
        message = prepare_email(
            self.member.as_email_recipient(), "t:{{ recipient.email }}"
        )
        self.assertIn(self.member.email, message.body)
        self.assertIn(self.member.email, message.alternatives[0][0])

    def test_markdown_default_subject(self):
        message = prepare_email(self.member.as_email_recipient(), "t:Body")
        self.assertEqual(message.subject, DEFAULT_SUBJECT)
        self.assertEqual(message.body, "Body")

    def test_markdown_subject(self):
        message = prepare_email(
            self.member.as_email_recipient(), "t:Subject: Custom\nBody"
        )
        self.assertEqual(message.subject, "Custom")
        self.assertEqual(message.body, "Body")

    def test_markdown_html_escape(self):
        message = prepare_email(self.member.as_email_recipient(), "t:1 < 2")
        self.assertIn("<", message.body)
        self.assertIn("&lt;", message.alternatives[0][0])

    def test_email_to_no_username(self):
        message = prepare_email(self.member.as_email_recipient(), "t:")
        self.assertEqual(message.to[0], "member@example.com")

    def test_email_to_username(self):
        self.member.username = "Member Username"
        message = prepare_email(self.member.as_email_recipient(), "t:")
        self.assertEqual(message.to[0], "Member Username <member@example.com>")

    def test_translation_en(self):
        message = prepare_email(
            self.member.as_email_recipient(),
            "t:{% load i18n %}{% blocktrans %}Translated text{% endblocktrans %}",
        )
        self.assertEqual(message.body, "Translated text")

    def test_translation_de(self):
        self.member.preferences.language = "de"
        # This translation is already provided by Django
        message = prepare_email(
            self.member.as_email_recipient(),
            "t:{% load i18n %}{% blocktrans %}German{% endblocktrans %}",
        )
        self.assertEqual(message.body, "Deutsch")

    def test_translation_before_subject(self):
        message = prepare_email(
            self.member.as_email_recipient(),
            "t:{% load i18n %}\nSubject: {% blocktrans %}Subject Line{% endblocktrans %}\n\n{% blocktrans %}Body{% endblocktrans %}",
        )
        self.assertEqual(message.subject, "Subject Line")
        self.assertEqual(message.body, "Body")

    def test_markdown_new_lines(self):
        message = prepare_email(
            self.member.as_email_recipient(), "t:Line one\nLine two"
        )
        self.assertIn("\n", message.body)
        # We want a new line, but it could show up as "<br>" or "<br />"
        self.assertIn("<br", message.alternatives[0][0])


class MemberCalfeedTest(FSTestCase):
    def setUp(self):
        self.super = Member.objects.create_user(email="a@b.c", is_superuser=True)
        self.band_admin = Member.objects.create_user(email="d@e.f")

        self.joeuser = Member.objects.create_user(email="g@h.i")
        self.joeuser.preferences.hide_canceled_gigs = False
        self.joeuser.preferences.calendar_show_only_confirmed = False
        self.joeuser.preferences.calendar_show_only_committed = False
        self.joeuser.preferences.save()

        self.janeuser = Member.objects.create_user(email="j@k.l")
        self.band = Band.objects.create(name="test band")
        Assoc.objects.create(
            member=self.joeuser,
            band=self.band,
            is_admin=True,
            status=AssocStatusChoices.CONFIRMED,
        )
        self.create_gig()

    def tearDown(self):
        """make sure we get rid of anything we made"""
        Member.objects.all().delete()
        Band.objects.all().delete()
        Assoc.objects.all().delete()
        Gig.objects.all().delete()

    def create_gig(self):
        the_date = timezone.datetime(
            2100, 1, 2, tzinfo=pytz.timezone(self.band.timezone)
        )
        return Gig.objects.create(
            title="New Gig",
            band_id=self.band.id,
            date=the_date,
            setdate=the_date + timedelta(minutes=30),
            enddate=the_date + timedelta(hours=2),
        )

    def make_caldav_stream(
        self,
        hide_canceled_gigs,
        calendar_show_only_confirmed,
        calendar_show_only_committed,
        gig_status,
        plan_answer,
        date=None,
    ):
        g = Gig.objects.first()
        m = self.joeuser
        p = Plan.objects.get(assoc__member=m.id, gig=g.id)

        m.preferences.hide_canceled_gigs = hide_canceled_gigs
        m.preferences.calendar_show_only_confirmed = calendar_show_only_confirmed
        m.preferences.calendar_show_only_committed = calendar_show_only_committed
        m.preferences.save()
        g.status = gig_status
        if date is not None:
            g.date = date
        g.save()
        p.status = plan_answer
        p.save()

        return prepare_calfeed(self.joeuser)

    def test_member_caldav_stream(self):
        # if we're filtering nothing, make sure we see the gig
        cf = self.make_caldav_stream(
            hide_canceled_gigs=False,
            calendar_show_only_confirmed=False,
            calendar_show_only_committed=False,
            gig_status=GigStatusChoices.CONFIRMED,
            plan_answer=PlanStatusChoices.DEFINITELY,
        )
        self.assertTrue(cf.find(b"EVENT") > 0)

    def test_member_caldav_stream_filter_canceled(self):
        # test hiding canceled gigs
        cf = self.make_caldav_stream(
            hide_canceled_gigs=True,
            calendar_show_only_confirmed=False,
            calendar_show_only_committed=False,
            gig_status=GigStatusChoices.CONFIRMED,
            plan_answer=PlanStatusChoices.DEFINITELY,
        )
        self.assertTrue(cf.find(b"EVENT") > 0)

        cf = self.make_caldav_stream(
            hide_canceled_gigs=True,
            calendar_show_only_confirmed=False,
            calendar_show_only_committed=False,
            gig_status=GigStatusChoices.CANCELLED,
            plan_answer=PlanStatusChoices.DEFINITELY,
        )
        self.assertEqual(cf.find(b"EVENT"), -1)

    def test_member_caldav_stream_filter_confirmed(self):
        # test showing only confirmed gigs
        cf = self.make_caldav_stream(
            hide_canceled_gigs=False,
            calendar_show_only_confirmed=True,
            calendar_show_only_committed=False,
            gig_status=GigStatusChoices.CANCELLED,
            plan_answer=PlanStatusChoices.DEFINITELY,
        )
        self.assertEqual(cf.find(b"EVENT"), -1)

    def test_member_caldav_stream_committed(self):
        # test showing only committed gigs
        cf = self.make_caldav_stream(
            hide_canceled_gigs=False,
            calendar_show_only_confirmed=False,
            calendar_show_only_committed=True,
            gig_status=GigStatusChoices.CONFIRMED,
            plan_answer=PlanStatusChoices.DONT_KNOW,
        )
        self.assertEqual(cf.find(b"EVENT"), -1)

    def test_member_caldav_stream_recent_only(self):
        # test showing only gigs in the last year
        cf = self.make_caldav_stream(
            hide_canceled_gigs=False,
            calendar_show_only_confirmed=False,
            calendar_show_only_committed=False,
            gig_status=GigStatusChoices.CONFIRMED,
            plan_answer=PlanStatusChoices.DEFINITELY,
            date=timezone.now() - timedelta(days=800),
        )
        self.assertEqual(cf.find(b"EVENT"), -1)

    def test_member_calfeed_bad_url(self):
        """fail on bad calfeed url"""
        self.setUpPyfakefs()  # fake a file system
        os.mkdir("calfeeds")

        # should fail due to bad calfeed id
        r = calfeed(request=None, pk="xyz")
        self.assertEqual(r.status_code, 404)

    def test_member_calfeed_url(self):
        """fake a file system"""
        self.setUpPyfakefs()  # fake a file system
        os.mkdir("calfeeds")

        # turn on dynamic calfeeds - worry about the queue version some other time
        settings.DYNAMIC_CALFEED = True

        self.joeuser.cal_feed_dirty = True
        self.joeuser.save()
        update_member_calfeed(self.joeuser.id)
        self.joeuser.refresh_from_db()
        # self.assertFalse(self.joeuser.cal_feed_dirty) # moved this to an async task

        cf = calfeed(request=None, pk=self.joeuser.cal_feed_id)
        self.assertTrue(cf.content.decode("ascii").find("EVENT") > 0)

    def test_calfeeds_dirty(self):
        self.joeuser.cal_feed_dirty = False
        self.joeuser.save()

        g = Gig.objects.first()
        g.title = "Edited"
        g.save()
        self.joeuser.refresh_from_db()
        self.assertTrue(self.joeuser.cal_feed_dirty)


class InviteTest(TemplateTestCase):
    def setUp(self):
        self.super = Member.objects.create_user(
            email="super@example.com", is_superuser=True
        )
        self.band_admin = Member.objects.create_user(email="admin@example.com")
        self.joeuser = Member.objects.create_user(email="joe@example.com")
        self.janeuser = Member.objects.create_user(email="jane@example.com")
        self.band = Band.objects.create(name="test band")
        Assoc.objects.create(
            member=self.band_admin,
            band=self.band,
            status=AssocStatusChoices.CONFIRMED,
            is_admin=True,
        )
        Assoc.objects.create(
            member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED
        )
        self.password = "sb8bBb5cGmE2uNn"  # Random value, but validates

        """ patch out the verify_captcha so we don't just fail """

        def mock_verify_captcha(*args, **kw):
            return True

        self.patcher = patch("member.views.verify_captcha", mock_verify_captcha)
        self.patcher.start()

    def tearDown(self):
        """make sure we get rid of anything we made"""
        Member.objects.all().delete()
        Band.objects.all().delete()
        Assoc.objects.all().delete()
        Invite.objects.all().delete()

    def test_invite_one(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(
            reverse("member-invite", args=[self.band.id]),
            {"emails": "new@example.com"},
            follow=True,
        )
        self.assertOK(response)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Invitations sent to new@example.com")
        self.assertEqual(Invite.objects.count(), 1)

    def test_invite_several(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(
            reverse("member-invite", args=[self.band.id]),
            {"emails": "new@example.com\ntwo@example.com"},
            follow=True,
        )
        self.assertOK(response)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Invitations sent to new@example.com, two@example.com"
        )
        self.assertEqual(Invite.objects.count(), 2)

    def test_invite_comma(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(
            reverse("member-invite", args=[self.band.id]),
            {"emails": "new@example.com,two@example.com"},
            follow=True,
        )
        self.assertOK(response)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "Invitations sent to new@example.com, two@example.com"
        )
        self.assertEqual(Invite.objects.count(), 2)

    def test_invite_existing(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(
            reverse("member-invite", args=[self.band.id]),
            {"emails": "joe@example.com"},
            follow=True,
        )
        self.assertOK(response)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            str(messages[0]), "These users are already in the band: joe@example.com"
        )
        self.assertEqual(Invite.objects.count(), 0)

    def test_invite_member(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(
            reverse("member-invite", args=[self.band.id]),
            {"emails": "jane@example.com"},
            follow=True,
        )
        self.assertOK(response)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Invitations sent to jane@example.com")
        self.assertEqual(Invite.objects.count(), 1)

    def test_invite_invalid(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(
            reverse("member-invite", args=[self.band.id]),
            {"emails": "notanemailaddress"},
            follow=True,
        )
        self.assertOK(response)
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Invalid email addresses: notanemailaddress")
        self.assertEqual(Invite.objects.count(), 0)

    def test_invite_gets_language(self):
        self.band_admin.preferences.language = "de"
        self.band_admin.preferences.save()
        self.client.force_login(self.band_admin)
        self.client.post(
            reverse("member-invite", args=[self.band.id]), {"emails": "new@example.com"}
        )
        self.assertEqual(
            Invite.objects.filter(email="new@example.com", language="de").count(), 1
        )

    def test_invite_super(self):
        self.client.force_login(self.super)
        response = self.client.post(
            reverse("member-invite", args=[self.band.id]),
            {"emails": "new@example.com"},
            follow=True,
        )
        self.assertOK(response)

    def test_invite_non_admin(self):
        self.client.force_login(self.joeuser)
        response = self.client.post(
            reverse("member-invite", args=[self.band.id]), {"emails": "new@example.com"}
        )
        self.assertIsInstance(response, HttpResponseForbidden)

    def test_invite_no_user(self):
        response = self.client.post(
            reverse("member-invite", args=[self.band.id]), {"emails": "new@example.com"}
        )
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertIn("/accounts/login", response.url)

    def test_invite_redirect_success(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(
            reverse("member-invite", args=[self.band.id]), {"emails": "new@example.com"}
        )
        self.assertRedirects(response, reverse("band-detail", args=[self.band.id]))

    def test_invite_redirect_error(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(
            reverse("member-invite", args=[self.band.id]),
            {"emails": "notanemailaddress"},
        )
        self.assertRedirects(response, reverse("member-invite", args=[self.band.id]))

    def test_invite_delete(self):
        invite = Invite.objects.create(email="new@example.com", band=self.band)
        self.client.force_login(self.band_admin)
        response = self.client.get(reverse("member-invite-delete", args=[invite.id]))
        self.assertRedirects(response, reverse("band-detail", args=[self.band.id]))
        self.assertEqual(Invite.objects.count(), 0)

    def test_invite_delete_own(self):
        invite = Invite.objects.create(email="jane@example.com", band=self.band)
        self.client.force_login(self.janeuser)
        response = self.client.get(reverse("member-invite-delete", args=[invite.id]))
        self.assertRedirects(
            response, reverse("member-detail", args=[self.janeuser.id])
        )
        self.assertEqual(Invite.objects.count(), 0)

    def test_invite_delete_super(self):
        invite = Invite.objects.create(email="new@example.com", band=self.band)
        self.client.force_login(self.super)
        response = self.client.get(reverse("member-invite-delete", args=[invite.id]))
        # The band-detail view currently fails if the user has no Assoc, so we
        # can't check if the redirected page actually loads.
        self.assertRedirects(
            response,
            reverse("band-detail", args=[self.band.id]),
            fetch_redirect_response=False,
        )
        self.assertEqual(Invite.objects.count(), 0)

    def test_invite_delete_non_admin(self):
        invite = Invite.objects.create(email="new@example.com", band=self.band)
        self.client.force_login(self.joeuser)
        response = self.client.get(reverse("member-invite-delete", args=[invite.id]))
        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertEqual(Invite.objects.count(), 1)

    def test_invite_delete_no_user(self):
        invite = Invite.objects.create(email="new@example.com", band=self.band)
        response = self.client.get(reverse("member-invite-delete", args=[invite.id]))
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertIn("/accounts/login", response.url)
        self.assertEqual(Invite.objects.count(), 1)

    def test_invite_email(self):
        Invite.objects.create(email="new@example.com", band=self.band)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["new@example.com"])

    def test_test_email(self):
        self.client.force_login(self.joeuser)
        self.assertEqual(len(mail.outbox), 0)
        _ = self.client.get(reverse("member-test-email"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["joe@example.com"])

    @flag_missing_vars
    def test_invite_new_email(self):
        invite = Invite.objects.create(email="new@example.com", band=self.band)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Invitation to Join Gig-o-Matic")
        self.assertIn(self.band.name, message.body)
        self.assertIn("get started", message.body)
        self.assertNotIn("existing", message.body)
        self.assertIn(reverse("member-invite-accept", args=[invite.id]), message.body)
        self.assertNotIn(MISSING, message.body)

    @flag_missing_vars
    def test_invite_existing_email(self):
        invite = Invite.objects.create(email=self.janeuser.email, band=self.band)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Gig-o-Matic New Band Invite")
        self.assertIn(self.band.name, message.body)
        self.assertNotIn("get started", message.body)
        self.assertIn("existing", message.body)
        self.assertIn(reverse("member-invite-accept", args=[invite.id]), message.body)
        self.assertNotIn(MISSING, message.body)

    @flag_missing_vars
    def test_invite_no_band_email(self):
        invite = Invite.objects.create(email="new@example.com", band=None)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Confirm your Email to Join Gig-o-Matic")
        self.assertIn(reverse("member-invite-accept", args=[invite.id]), message.body)
        self.assertNotIn(MISSING, message.body)

    def test_accept_invite_logged_in(self):
        invite = Invite.objects.create(email="jane@example.com", band=self.band)
        self.client.force_login(self.janeuser)
        response = self.client.get(reverse("member-invite-accept", args=[invite.id]))
        self.assertRedirects(
            response, reverse("member-detail", args=[self.janeuser.id])
        )
        self.assertEqual(
            Assoc.objects.filter(band=self.band, member=self.janeuser).count(), 1
        )
        self.assertEqual(Invite.objects.count(), 0)

    def test_accept_invite_logged_in_no_band(self):
        invite = Invite.objects.create(email="jane@example.com")
        self.client.force_login(self.janeuser)
        response = self.client.get(reverse("member-invite-accept", args=[invite.id]))
        self.assertRedirects(
            response, reverse("member-detail", args=[self.janeuser.id])
        )
        self.assertEqual(Assoc.objects.filter(member=self.janeuser).count(), 0)
        self.assertEqual(Invite.objects.count(), 0)

    def test_accept_invite_logged_out(self):
        invite = Invite.objects.create(email="jane@example.com", band=self.band)
        response = self.client.get(reverse("member-invite-accept", args=[invite.id]))
        self.assertOK(response)
        self.assertTemplateUsed(response, "member/accepted.html")
        self.assertEqual(
            Assoc.objects.filter(band=self.band, member=self.janeuser).count(), 1
        )
        self.assertEqual(Invite.objects.count(), 0)

    def test_accept_invite_logged_out_no_band(self):
        invite = Invite.objects.create(email="jane@example.com", band=None)
        response = self.client.get(reverse("member-invite-accept", args=[invite.id]))
        self.assertOK(response)
        self.assertTemplateUsed(response, "member/accepted.html")
        self.assertEqual(Assoc.objects.filter(member=self.janeuser).count(), 0)
        self.assertEqual(Invite.objects.count(), 0)

    def test_accept_invite_logged_in_other(self):
        n_assoc = Assoc.objects.count()
        invite = Invite.objects.create(email="jane@example.com", band=self.band)
        self.client.force_login(self.joeuser)
        response = self.client.get(reverse("member-invite-accept", args=[invite.id]))
        self.assertOK(response)
        self.assertTemplateUsed(response, "member/claim_invite.html")
        self.assertIn(b"accept the invite as", response.content)
        self.assertEqual(Invite.objects.count(), 1)  # Didn't delete the invite
        # Didn't create an Assoc
        self.assertEqual(Assoc.objects.count(), n_assoc)

    def test_accept_invite_logged_in_other_no_band(self):
        # Note that this is a completely weird state to get into.  This test is merely to
        # check that nothing blows up.
        n_assoc = Assoc.objects.count()
        invite = Invite.objects.create(email="jane@example.com", band=None)
        self.client.force_login(self.joeuser)
        response = self.client.get(reverse("member-invite-accept", args=[invite.id]))
        self.assertOK(response)
        self.assertTemplateUsed(response, "member/claim_invite.html")
        self.assertIn(b"accept the invite as", response.content)
        self.assertEqual(Invite.objects.count(), 1)  # Didn't delete the invite
        # Didn't create an Assoc
        self.assertEqual(Assoc.objects.count(), n_assoc)

    def test_accept_invite_no_member_logged_in(self):
        n_assoc = Assoc.objects.count()
        invite = Invite.objects.create(email="new@example.com", band=self.band)
        self.client.force_login(self.joeuser)
        response = self.client.get(reverse("member-invite-accept", args=[invite.id]))
        self.assertOK(response)
        self.assertTemplateUsed(response, "member/claim_invite.html")
        self.assertIn(b"create an account for", response.content)
        self.assertEqual(Invite.objects.count(), 1)  # Didn't delete the invite
        # Didn't create an Assoc
        self.assertEqual(Assoc.objects.count(), n_assoc)

    def test_accept_invite_no_member_logged_in_no_band(self):
        n_assoc = Assoc.objects.count()
        invite = Invite.objects.create(email="new@example.com", band=None)
        self.client.force_login(self.joeuser)
        response = self.client.get(reverse("member-invite-accept", args=[invite.id]))
        self.assertOK(response)
        self.assertTemplateUsed(response, "member/claim_invite.html")
        self.assertIn(b"create an account for", response.content)
        self.assertEqual(Invite.objects.count(), 1)  # Didn't delete the invite
        # Didn't create an Assoc
        self.assertEqual(Assoc.objects.count(), n_assoc)

    def test_accept_invite_no_member_logged_out(self):
        n_assoc = Assoc.objects.count()
        invite = Invite.objects.create(email="new@example.com", band=self.band)
        response = self.client.get(reverse("member-invite-accept", args=[invite.id]))
        self.assertRedirects(response, reverse("member-create", args=[invite.id]))
        self.assertEqual(Invite.objects.count(), 1)  # Didn't delete the invite
        # Didn't create an Assoc
        self.assertEqual(Assoc.objects.count(), n_assoc)

    def test_accept_invite_no_member_logged_out_no_band(self):
        n_assoc = Assoc.objects.count()
        invite = Invite.objects.create(email="new@example.com", band=None)
        response = self.client.get(reverse("member-invite-accept", args=[invite.id]))
        self.assertRedirects(response, reverse("member-create", args=[invite.id]))
        self.assertEqual(Invite.objects.count(), 1)  # Didn't delete the invite
        # Didn't create an Assoc
        self.assertEqual(Assoc.objects.count(), n_assoc)

    def test_accept_invite_claim(self):
        invite = Invite.objects.create(email="new@example.com", band=self.band)
        self.client.force_login(self.janeuser)
        response = self.client.get(
            reverse("member-invite-accept", args=[invite.id]), {"claim": "true"}
        )
        self.assertRedirects(
            response, reverse("member-detail", args=[self.janeuser.id])
        )
        self.assertEqual(
            Assoc.objects.filter(band=self.band, member=self.janeuser).count(), 1
        )
        self.assertEqual(Invite.objects.count(), 0)

    def test_accept_invite_duplicate_assoc(self):
        invite = Invite.objects.create(email="joe@example.com", band=self.band)
        self.client.force_login(self.joeuser)
        response = self.client.get(
            reverse("member-invite-accept", args=[invite.id]), {"claim": "true"}
        )
        self.assertRedirects(response, reverse("member-detail", args=[self.joeuser.id]))
        self.assertEqual(
            Assoc.objects.filter(band=self.band, member=self.joeuser).count(), 1
        )
        self.assertEqual(Invite.objects.count(), 0)

    def test_invite_sets_language(self):
        invite = Invite.objects.create(
            email="jane@example.com", band=self.band, language="de"
        )
        self.client.get(reverse("member-invite-accept", args=[invite.id]))
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, "de")

    def test_invite_uses_language(self):
        invite = Invite.objects.create(
            email="jane@example.com", band=self.band, language="de"
        )
        with self.assertRenderLanguage("de", "member.views.render"):
            self.client.get(reverse("member-invite-accept", args=[invite.id]))

    def test_invite_sets_language_on_redirect(self):
        invite = Invite.objects.create(
            email="new@example.com", band=self.band, language="de"
        )
        self.client.get(reverse("member-invite-accept", args=[invite.id]))
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, "de")

    def test_invite_does_not_override_language(self):
        invite = Invite.objects.create(
            email="jane@example.com", band=self.band, language="de"
        )
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en-us"
        self.client.get(reverse("member-invite-accept", args=[invite.id]))
        self.assertEqual(
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, "en-us"
        )

    def test_accept_invite_invalid_invite(self):
        invite = Invite.objects.create(email="jane@example.com", band=self.band)
        the_id = invite.id
        invite.delete()
        response = self.client.get(reverse("member-invite-accept", args=[the_id]))
        self.assertOK(response)
        self.assertTemplateUsed(response, "member/invite_expired.html")

    def test_create_member(self):
        invite = Invite.objects.create(email="new@example.com", band=self.band)
        response = self.client.post(
            reverse("member-create", args=[invite.id]),
            {
                "username": "New",
                "nickname": "new",
                "password1": self.password,
                "password2": self.password,
            },
        )
        # We redirect to the accept invite page, which redirects to the member profile
        self.assertRedirects(
            response,
            reverse("member-invite-accept", args=[invite.id]),
            target_status_code=302,
        )
        new = Member.objects.filter(email="new@example.com").get()
        self.assertEqual(new.username, "New")
        self.assertEqual(new.nickname, "new")

    def test_create_member_no_band(self):
        invite = Invite.objects.create(email="new@example.com", band=None)
        response = self.client.post(
            reverse("member-create", args=[invite.id]),
            {
                "username": "New",
                "nickname": "new",
                "password1": self.password,
                "password2": self.password,
            },
        )
        # We redirect to the accept invite page, which redirects to the member profile
        self.assertRedirects(
            response,
            reverse("member-invite-accept", args=[invite.id]),
            target_status_code=302,
        )
        new = Member.objects.filter(email="new@example.com").get()
        self.assertEqual(new.username, "New")
        self.assertEqual(new.nickname, "new")

    def test_create_member_full_redirect(self):
        invite = Invite.objects.create(email="new@example.com", band=self.band)
        response = self.client.post(
            reverse("member-create", args=[invite.id]),
            {
                "username": "New",
                "nickname": "new",
                "password1": self.password,
                "password2": self.password,
            },
            follow=True,
        )
        self.assertOK(response)
        self.assertTemplateUsed(response, "member/member_detail.html")

    def test_create_duplicate_member(self):
        invite = Invite.objects.create(email="jane@example.com", band=self.band)
        response = self.client.post(
            reverse("member-create", args=[invite.id]),
            {
                "username": "New",
                "nickname": "new",
                "password1": self.password,
                "password2": self.password,
            },
        )
        self.assertOK(response)
        self.assertIn(b"already exists", response.content)
        self.assertEqual(Member.objects.filter(email="jane@example.com").count(), 1)

    def test_create_bad_password(self):
        invite = Invite.objects.create(email="new@example.com", band=self.band)
        response = self.client.post(
            reverse("member-create", args=[invite.id]),
            {
                "username": "New",
                "nickname": "new",
                "password1": self.password,
                "password2": "54321",
            },
        )
        self.assertOK(response)
        self.assertIn(
            b"The two password fields didn\xe2\x80\x99t match.", response.content
        )
        self.assertEqual(Member.objects.filter(email="new@example.com").count(), 0)

    def test_create_gets_logged_in(self):
        invite = Invite.objects.create(email="new@example.com", band=self.band)
        self.client.post(
            reverse("member-create", args=[invite.id]),
            {
                "username": "New",
                "nickname": "new",
                "password1": self.password,
                "password2": self.password,
            },
        )
        self.assertTrue(auth.get_user(self.client).is_authenticated)

    def test_create_gets_invite_language(self):
        invite = Invite.objects.create(
            email="new@example.com", band=self.band, language="de"
        )
        self.client.post(
            reverse("member-create", args=[invite.id]),
            {
                "username": "New",
                "nickname": "new",
                "password1": self.password,
                "password2": self.password,
            },
        )
        new_member = Member.objects.get(email="new@example.com")
        self.assertEqual(new_member.preferences.language, "de")
        self.assertTrue(auth.get_user(self.client).is_authenticated)

    def test_signup(self):

        response = self.client.post(
            reverse("member-signup"), {"email": "new@example.com"}
        )
        self.assertOK(response)
        self.assertTemplateUsed(response, "member/signup_pending.html")
        self.assertEqual(
            Invite.objects.filter(email="new@example.com", band=None).count(), 1
        )

    def test_signup_duplicate(self):
        response = self.client.post(
            reverse("member-signup"), {"email": "joe@example.com"}, follow=True
        )
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('home')}")
        self.assertEqual(Invite.objects.filter(email="joe@example.com").count(), 0)

    def test_signup_invalid(self):
        response = self.client.post(reverse("member-signup"), {"email": "invalid"})
        self.assertOK(response)
        self.assertTemplateUsed(response, "member/signup.html")
        self.assertEqual(Invite.objects.filter(email="invalid").count(), 0)


class MemberDeleteTest(TestCase):
    def setUp(self):
        self.super = Member.objects.create_user(email="super@b.c", is_superuser=True)
        self.band_admin = Member.objects.create_user(email="admin@e.f")
        self.joeuser = Member.objects.create_user(email="joeuser@h.i")
        self.janeuser = Member.objects.create_user(email="janeuser@k.l")
        self.band = Band.objects.create(
            name="test band", timezone="UTC", anyone_can_create_gigs=True
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
        self.assertEqual(Assoc.objects.all().count(), 0)  # should all be gone!
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

        # should get a redirect to the gig info page
        self.assertEqual(response.status_code, expect_code)
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
        # should get a redirect to the gig info page
        self.assertEqual(response.status_code, expect_code)
        self.assertEqual(Gig.objects.count(), 1)
        the_gig.refresh_from_db()
        return the_gig

    def assoc_joe(self):
        a = Assoc.objects.create(
            member=self.joeuser, band=self.band, status=AssocStatusChoices.CONFIRMED
        )
        return a

    def assoc_joe_and_create_gig(self, **kwargs):
        a = self.assoc_joe()
        g = self.create_gig_form(contact=self.joeuser, **kwargs)
        p = g.member_plans.filter(assoc=a).get() if g else None
        return g, a, p

    def test_delete_member(self):
        self.assertEqual(self.joeuser.status, MemberStatusChoices.ACTIVE)
        self.assertTrue(self.joeuser.is_active)
        self.joeuser.delete()
        self.assertEqual(self.joeuser.status, MemberStatusChoices.DELETED)
        self.assertFalse(self.joeuser.is_active)

    # test deleting user sets email address to something anonymous
    def test_delete_member_email(self):
        self.assertEqual(self.joeuser.email, "joeuser@h.i")
        self.joeuser.delete()
        self.assertEqual(
            self.joeuser.email, "user_{0}@gig-o-matic.com".format(self.joeuser.id)
        )

    # test creating a gig does not create a plan for a deleted user
    def test_delete_member_noplans(self):
        g, _, _ = self.assoc_joe_and_create_gig(user=self.band_admin)
        self.assertEqual(Plan.objects.filter(gig=g).count(), 2)
        Plan.objects.all().delete()
        self.joeuser.delete()
        g2 = self.create_gig_form(contact=self.band_admin, user=self.band_admin)
        self.assertEqual(Plan.objects.filter(gig=g2).count(), 1)

    # test deleting a user also deletes gig plans for future gigs
    def test_delete_future_plans(self):
        g, _, _ = self.assoc_joe_and_create_gig(user=self.band_admin)
        self.assertEqual(Plan.objects.filter(gig=g).count(), 2)
        self.joeuser.delete()
        self.assertEqual(Plan.objects.filter(gig=g).count(), 1)

    # test deleted users don't show up on gig detail page
    def test_deleted_member_plans_detail(self):
        g, _, _ = self.assoc_joe_and_create_gig(user=self.band_admin)
        p = g.member_plans
        self.assertEqual(p.count(), 2)
        self.joeuser.delete()
        p2 = g.member_plans
        self.assertEqual(p2.count(), 1)

    # test deleted users show up on gig archive page
    def test_deleted_member_plans_archive(self):
        g, _, _ = self.assoc_joe_and_create_gig(user=self.band_admin)
        p = g.member_plans
        self.assertEqual(p.count(), 2)
        g.is_archived = True
        g.save()
        self.joeuser.delete()
        p2 = g.member_plans
        self.assertEqual(p2.count(), 2)

    # test logging in not allowed for deleted user
    def test_login_delete(self):
        self.client.logout()
        self.joeuser.set_password("ThisIsPass716")
        self.joeuser.save()
        self.assertTrue(
            self.client.login(email=self.joeuser.email, password="ThisIsPass716")
        )
        self.joeuser.delete()
        self.assertFalse(
            self.client.login(email=self.joeuser.email, password="ThisIsPass716")
        )

    # test deleting user erases phone and statement
    def test_delete_personal_info(self):
        self.joeuser.phone = "123-4567"
        self.joeuser.statement = "Cogito Ergo Sum"
        self.joeuser.save()
        self.joeuser.delete()
        self.assertEqual(self.joeuser.phone, "")
        self.assertEqual(self.joeuser.statement, "")


class MemberEditTest(TemplateTestCase):
    def setUp(self):
        self.joeuser = Member.objects.create_user("a@b.com", password="abc")
        self.jilluser = Member.objects.create_user("c@d.com", password="def")
        b = Band.objects.create(name="test band")
        Assoc.objects.create(band=b, member=self.joeuser)
        Assoc.objects.create(band=b, member=self.jilluser)
        Band.objects.create(name="another band")

    def tearDown(self):
        """make sure we get rid of anything we made"""
        Member.objects.all().delete()
        self.assertEqual(Assoc.objects.all().count(), 0)  # should all be gone!
        Band.objects.all().delete()
        Assoc.objects.all().delete()

    def test_member_view(self):
        self.client.force_login(self.joeuser)
        response = self.client.get("/member", follow=True)
        self.assertOK(response)

    def test_member_view2(self):
        self.client.force_login(self.joeuser)
        response = self.client.get(
            reverse("member-detail", args=[self.joeuser.id]), follow=True
        )
        self.assertOK(response)

    def test_member_view3(self):
        self.client.force_login(self.joeuser)
        response = self.client.get(
            reverse("member-detail", args=[self.jilluser.id]), follow=True
        )
        self.assertPermissionDenied(response)

    def test_member_edit(self):
        self.client.force_login(self.joeuser)
        response = self.client.post(
            reverse("member-update", args=[self.joeuser.id]), follow=True
        )
        self.assertOK(response)
        response = self.client.get(
            reverse("member-update", args=[self.joeuser.id]), follow=True
        )
        self.assertOK(response)

    def test_another_member_edit(self):
        self.client.force_login(self.joeuser)
        response = self.client.post(
            reverse("member-update", args=[self.jilluser.id]), follow=True
        )
        self.assertPermissionDenied(response)
        response = self.client.get(
            reverse("member-update", args=[self.jilluser.id]), follow=True
        )
        self.assertPermissionDenied(response)

    def test_member_prefs_edit(self):
        self.client.force_login(self.joeuser)
        response = self.client.post(
            reverse("member-prefs-update", args=[self.joeuser.id]), follow=True
        )
        self.assertOK(response)
        response = self.client.get(
            reverse("member-prefs-update", args=[self.joeuser.id]), follow=True
        )
        self.assertOK(response)

    def test_another_member_prefs_edit(self):
        self.client.force_login(self.joeuser)
        response = self.client.post(
            reverse("member-prefs-update", args=[self.jilluser.id]), follow=True
        )
        self.assertPermissionDenied(response)
        response = self.client.get(
            reverse("member-prefs-update", args=[self.jilluser.id]), follow=True
        )
        self.assertPermissionDenied(response)

    def test_change_email(self):
        self.client.force_login(self.joeuser)
        response = self.client.post(
            reverse("member-update", args=[self.joeuser.id]),
            {"username": "joey", "email": "foo@bar.com"},
            follow=True,
        )
        self.assertOK(response)
        self.assertTrue(self.joeuser.pending_email.count() == 1)
        self.assertTrue(self.joeuser.pending_email.first().new_email == "foo@bar.com")

        self.assertTrue(len(mail.outbox), 1)
        self.assertTrue(mail.outbox[0].subject.find("Email Confirmation") > 0)

        response = self.client.post(
            reverse("member-update", args=[self.joeuser.id]),
            data={"email": "janeuser@k.l"},
            follow=True,
        )
        self.assertOK(response)
        self.assertTrue(self.joeuser.pending_email.count() == 1)
        self.assertTrue(self.joeuser.pending_email.first().new_email == "foo@bar.com")

        response = self.client.get(
            reverse(
                "member-confirm-email", args=[self.joeuser.pending_email.first().id]
            ),
            follow=True,
        )
        self.joeuser.refresh_from_db()
        self.assertTrue(self.joeuser.email == "foo@bar.com")


class GraphQLTest(TestCase):
    def setUp(self):
        self.super = Member.objects.create_user(email="super@b.c", is_superuser=True)
        self.band_admin = Member.objects.create_user(email="admin@e.f")
        self.joeuser = Member.objects.create_user(email="joe@h.i")
        self.janeuser = Member.objects.create_user(email="jane@k.l")
        """ set context for test graphene requests """
        self.request_factory = RequestFactory()
        self.context_value = self.request_factory.get("/api/")

    def tearDown(self):
        """make sure we get rid of anything we made"""
        Member.objects.all().delete()

    # test member queries
    def test_all_members_superuser(self):
        client = graphQLClient(schema)
        self.context_value.user = self.super
        executed = client.execute(
            """{ allMembers{
            email,
            username
            } }""",
            context_value=self.context_value,
        )
        assert executed == {
            "data": {
                "allMembers": [
                    {"email": "super@b.c", "username": ""},
                    {"email": "admin@e.f", "username": ""},
                    {"email": "joe@h.i", "username": ""},
                    {"email": "jane@k.l", "username": ""},
                ]
            }
        }

    def test_all_members_not_superuser(self):
        client = graphQLClient(schema)
        self.context_value.user = self.joeuser
        executed = client.execute(
            """{ allMembers{
            email,
            username
            } }""",
            context_value=self.context_value,
        )
        assert "errors" in executed

    def test_member_by_email_superuser(self):
        client = graphQLClient(schema)
        self.context_value.user = self.super
        executed = client.execute(
            """{ memberByEmail(email:"joe@h.i") {
            email,
            username
            } }""",
            context_value=self.context_value,
        )
        assert executed == {
            "data": {"memberByEmail": {"email": "joe@h.i", "username": ""}}
        }

    def test_member_by_email_not_superuser(self):
        client = graphQLClient(schema)
        self.context_value.user = self.joeuser
        executed = client.execute(
            """{ memberByEmail(email:"joe@h.i") {
            email,
            username
            } }""",
            context_value=self.context_value,
        )
        assert "errors" in executed


class MemberSecurityTest(GigTestBase):
    def test_member_detail_access(self):
        c = Client()
        c.force_login(self.joeuser)

        # can see myself
        response = c.get(reverse("member-detail"))
        self.assertEqual(response.status_code, 200)
        response = c.get(reverse("member-detail", args=[self.joeuser.id]))

        _, _, _ = self.assoc_joe_and_create_gig()
        response = c.get(reverse("member-detail", args=[self.janeuser.id]))
        self.assertEqual(
            response.status_code, 403
        )  # fail if we're not in the same band

        self.assoc_user(self.janeuser)
        response = c.get(reverse("member-detail", args=[self.janeuser.id]))
        self.assertEqual(response.status_code, 200)
