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
from .models import Member, MemberPreferences, Invite
from band.models import Band, Assoc
from gig.models import Gig, Plan
from .views import AssocsView, OtherBandsView
from .helpers import prepare_calfeed, calfeed, update_all_calfeeds
from lib.email import DEFAULT_SUBJECT, prepare_email
from lib.template_test import MISSING, flag_missing_vars
from django.conf import settings
from django.contrib import auth
from django.core import mail
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import resolve, reverse
from django.utils import timezone, translation
from datetime import timedelta
import pytz
import os
from pyfakefs.fake_filesystem_unittest import TestCase as FSTestCase


class MemberTest(TestCase):
    def setUp(self):
        m = Member.objects.create_user('a@b.com', password='abc')
        b = Band.objects.create(name='test band')
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
        self.assertEqual(len(m.assocs.all()), 1)
        b = m.assocs.first().band
        self.assertEqual(b.name, 'test band')

    def test_memberassocsview(self):
        m = Member.objects.first()
        request = RequestFactory().get('/member/{}/assocs/'.format(m.id))
        view = AssocsView()
        view.setup(request, pk='{}'.format(m.id))

        context = view.get_context_data()
        self.assertIn('assocs', context)
        self.assertEqual(len(context['assocs']), 1)
        self.assertEqual(context['assocs'][0].band.name, 'test band')

    def test_member_otherbandsview(self):
        m = Member.objects.first()
        request = RequestFactory().get('/member/{}/otherbands/'.format(m.id))
        view = OtherBandsView()
        view.setup(request, pk='{}'.format(m.id))

        context = view.get_context_data()
        self.assertIn('bands', context)
        self.assertEqual(len(context['bands']), 1)
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
        message = prepare_email(self.member.as_email_recipient(), 't:**Markdown**')
        self.assertIn('**Markdown**', message.body)
        self.assertEqual(len(message.alternatives), 1)
        self.assertEqual(message.alternatives[0][1], 'text/html')
        self.assertIn('<strong>Markdown</strong>', message.alternatives[0][0])

    def test_markdown_template(self):
        message = prepare_email(self.member.as_email_recipient(), 't:{{ key }}', {'key': 'value'})
        self.assertIn('value', message.body)
        self.assertIn('value', message.alternatives[0][0])

    def test_markdown_template_member(self):
        message = prepare_email(self.member.as_email_recipient(), 't:{{ recipient.email }}')
        self.assertIn(self.member.email, message.body)
        self.assertIn(self.member.email, message.alternatives[0][0])

    def test_markdown_default_subject(self):
        message = prepare_email(self.member.as_email_recipient(), 't:Body')
        self.assertEqual(message.subject, DEFAULT_SUBJECT)
        self.assertEqual(message.body, 'Body')

    def test_markdown_subject(self):
        message = prepare_email(self.member.as_email_recipient(), 't:Subject: Custom\nBody')
        self.assertEqual(message.subject, 'Custom')
        self.assertEqual(message.body, 'Body')

    def test_markdown_html_escape(self):
        message = prepare_email(self.member.as_email_recipient(), 't:1 < 2')
        self.assertIn('<', message.body)
        self.assertIn('&lt;', message.alternatives[0][0])

    def test_email_to_no_username(self):
        message = prepare_email(self.member.as_email_recipient(), 't:')
        self.assertEqual(message.to[0], 'member@example.com')

    def test_email_to_username(self):
        self.member.username = 'Member Username'
        message = prepare_email(self.member.as_email_recipient(), 't:')
        self.assertEqual(message.to[0], 'Member Username <member@example.com>')

    def test_translation_en(self):
        message = prepare_email(
            self.member.as_email_recipient(),
            't:{% load i18n %}{% blocktrans %}Translated text{% endblocktrans %}'
        )
        self.assertEqual(message.body, 'Translated text')

    def test_translation_de(self):
        self.member.preferences.language = 'de'
        # This translation is already provided by Django
        message = prepare_email(
            self.member.as_email_recipient(),
            't:{% load i18n %}{% blocktrans %}German{% endblocktrans %}'
        )
        self.assertEqual(message.body, 'Deutsch')

    def test_translation_before_subject(self):
        message = prepare_email(
            self.member.as_email_recipient(),
            't:{% load i18n %}\nSubject: {% blocktrans %}Subject Line{% endblocktrans %}\n\n{% blocktrans %}Body{% endblocktrans %}'
        )
        self.assertEqual(message.subject, "Subject Line")
        self.assertEqual(message.body, "Body")

    def test_markdown_new_lines(self):
        message = prepare_email(self.member.as_email_recipient(), 't:Line one\nLine two')
        self.assertIn('\n', message.body)
        # We want a new line, but it could show up as "<br>" or "<br />"
        self.assertIn('<br', message.alternatives[0][0])


class MemberCalfeedTest(FSTestCase):
    def setUp(self):
        self.super = Member.objects.create_user(
            email='a@b.c', is_superuser=True)
        self.band_admin = Member.objects.create_user(email='d@e.f')

        self.joeuser = Member.objects.create_user(email='g@h.i')
        self.joeuser.preferences.hide_canceled_gigs = False
        self.joeuser.preferences.calendar_show_only_confirmed = False
        self.joeuser.preferences.calendar_show_only_committed = False
        self.joeuser.preferences.save()

        self.janeuser = Member.objects.create_user(email='j@k.l')
        self.band = Band.objects.create(name='test band')
        Assoc.objects.create(member=self.joeuser,
                             band=self.band, is_admin=True)
        self.create_gig()

    def tearDown(self):
        """ make sure we get rid of anything we made """
        Member.objects.all().delete()
        Band.objects.all().delete()
        Assoc.objects.all().delete()
        Gig.objects.all().delete()

    def create_gig(self):
        the_date = timezone.datetime(
            2100, 1, 2, tzinfo=pytz.timezone(self.band.timezone))
        return Gig.objects.create(
            title="New Gig",
            band_id=self.band.id,
            date=the_date,
            setdate=the_date + timedelta(minutes=30),
            enddate=the_date + timedelta(hours=2)
        )

    def make_caldav_stream(self,
                           hide_canceled_gigs,
                           calendar_show_only_confirmed,
                           calendar_show_only_committed,
                           gig_status,
                           plan_answer,
                           date=None):
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
            gig_status=Gig.StatusOptions.CONFIRMED,
            plan_answer=Plan.StatusChoices.DEFINITELY
        )
        self.assertTrue(cf.find(b'EVENT') > 0)

    def test_member_caldav_stream_filter_canceled(self):
        # test hiding canceled gigs
        cf = self.make_caldav_stream(
            hide_canceled_gigs=True,
            calendar_show_only_confirmed=False,
            calendar_show_only_committed=False,
            gig_status=Gig.StatusOptions.CONFIRMED,
            plan_answer=Plan.StatusChoices.DEFINITELY
        )
        self.assertTrue(cf.find(b'EVENT') > 0)

        cf = self.make_caldav_stream(
            hide_canceled_gigs=True,
            calendar_show_only_confirmed=False,
            calendar_show_only_committed=False,
            gig_status=Gig.StatusOptions.CANCELLED,
            plan_answer=Plan.StatusChoices.DEFINITELY
        )
        self.assertEqual(cf.find(b'EVENT'), -1)

    def test_member_caldav_stream_filter_confirmed(self):
        # test showing only confirmed gigs
        cf = self.make_caldav_stream(
            hide_canceled_gigs=False,
            calendar_show_only_confirmed=True,
            calendar_show_only_committed=False,
            gig_status=Gig.StatusOptions.CANCELLED,
            plan_answer=Plan.StatusChoices.DEFINITELY
        )
        self.assertEqual(cf.find(b'EVENT'), -1)

    def test_member_caldav_stream_committed(self):
        # test showing only committed gigs
        cf = self.make_caldav_stream(
            hide_canceled_gigs=False,
            calendar_show_only_confirmed=False,
            calendar_show_only_committed=True,
            gig_status=Gig.StatusOptions.CONFIRMED,
            plan_answer=Plan.StatusChoices.DONT_KNOW
        )
        self.assertEqual(cf.find(b'EVENT'), -1)

    def test_member_caldav_stream_recent_only(self):
        # test showing only gigs in the last year
        cf = self.make_caldav_stream(
            hide_canceled_gigs=False,
            calendar_show_only_confirmed=False,
            calendar_show_only_committed=False,
            gig_status=Gig.StatusOptions.CONFIRMED,
            plan_answer=Plan.StatusChoices.DEFINITELY,
            date=timezone.now() - timedelta(days=800)
        )
        self.assertEqual(cf.find(b'EVENT'), -1)

    def test_member_calfeed_bad_url(self):
        """ fail on bad calfeed url """
        self.setUpPyfakefs()    # fake a file system
        os.mkdir('calfeeds')

        # should fail due to bad calfeed id
        r = calfeed(request=None, pk='xyz')
        self.assertEqual(r.status_code, 404)

    def test_member_calfeed_url(self):
        """ fake a file system """
        self.setUpPyfakefs()    # fake a file system
        os.mkdir('calfeeds')

        self.joeuser.cal_feed_dirty = True
        self.joeuser.save()
        update_all_calfeeds()
        self.joeuser.refresh_from_db()
        self.assertFalse(self.joeuser.cal_feed_dirty)

        cf = calfeed(request=None, pk=self.joeuser.cal_feed_id)
        self.assertTrue(cf.content.decode('ascii').find('EVENT') > 0)

    def test_calfeeds_dirty(self):
        self.joeuser.cal_feed_dirty = False
        self.joeuser.save()

        g = Gig.objects.first()
        g.title = "Edited"
        g.save()
        self.joeuser.refresh_from_db()
        self.assertTrue(self.joeuser.cal_feed_dirty)


class InviteTest(TestCase):
    def setUp(self):
        self.super = Member.objects.create_user(email='super@example.com', is_superuser=True)
        self.band_admin = Member.objects.create_user(email='admin@example.com')
        self.joeuser = Member.objects.create_user(email='joe@example.com')
        self.janeuser = Member.objects.create_user(email='jane@example.com')
        self.band = Band.objects.create(name='test band')
        Assoc.objects.create(member=self.band_admin, band=self.band, is_admin=True)
        Assoc.objects.create(member=self.joeuser, band=self.band)
        self.password = 'sb8bBb5cGmE2uNn'  # Random value, but validates

    def tearDown(self):
        """ make sure we get rid of anything we made """
        Member.objects.all().delete()
        Band.objects.all().delete()
        Assoc.objects.all().delete()
        Invite.objects.all().delete()

    def assertOK(self, response):
        self.assertEqual(response.status_code, 200)

    def assertRenderLanguage(self, lang, render_cmd='django.shortcuts.render'):
        test_case = self

        class LanguageReport(Exception):
            def __init__(self, lang):
                self.lang = lang

        def fake_render(*args, **kw):
            raise LanguageReport(translation.get_language())

        class RenderLanguageContextManager:

            def __enter__(self):
                self.patcher = patch(render_cmd, fake_render)
                self.patcher.start()

            def __exit__(self, exc_type, exc_value, tb):
                self.patcher.stop()
                if exc_type is None:
                    test_case.fail("Render code was not called")
                if isinstance(exc_value, LanguageReport):
                    if exc_value.lang != lang:
                        test_case.fail(f"Language when render was called was {exc_value.lang}; expected to be {lang}")
                    return True
                return False  # Other errors will be raised

        return RenderLanguageContextManager()

    def test_invite_one(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(reverse('member-invite', args=[self.band.id]),
            {'emails': 'new@example.com'}, follow=True)
        self.assertOK(response)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Invitations sent to new@example.com')
        self.assertEqual(Invite.objects.count(), 1)

    def test_invite_several(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(reverse('member-invite', args=[self.band.id]),
            {'emails': 'new@example.com\ntwo@example.com'}, follow=True)
        self.assertOK(response)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Invitations sent to new@example.com, two@example.com')
        self.assertEqual(Invite.objects.count(), 2)

    def test_invite_comma(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(reverse('member-invite', args=[self.band.id]),
            {'emails': 'new@example.com,two@example.com'}, follow=True)
        self.assertOK(response)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Invitations sent to new@example.com, two@example.com')
        self.assertEqual(Invite.objects.count(), 2)

    def test_invite_existing(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(reverse('member-invite', args=[self.band.id]),
            {'emails': 'joe@example.com'}, follow=True)
        self.assertOK(response)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'These users are already in the band: joe@example.com')
        self.assertEqual(Invite.objects.count(), 0)

    def test_invite_member(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(reverse('member-invite', args=[self.band.id]),
            {'emails': 'jane@example.com'}, follow=True)
        self.assertOK(response)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Invitations sent to jane@example.com')
        self.assertEqual(Invite.objects.count(), 1)

    def test_invite_invalid(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(reverse('member-invite', args=[self.band.id]),
            {'emails': 'notanemailaddress'}, follow=True)
        self.assertOK(response)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Invalid email addresses: notanemailaddress')
        self.assertEqual(Invite.objects.count(), 0)

    def test_invite_gets_language(self):
        self.band_admin.preferences.language = 'de'
        self.band_admin.preferences.save()
        self.client.force_login(self.band_admin)
        self.client.post(reverse('member-invite', args=[self.band.id]),
            {'emails': 'new@example.com'})
        self.assertEqual(Invite.objects.filter(email='new@example.com', language='de').count(), 1)

    def test_invite_super(self):
        self.client.force_login(self.super)
        response = self.client.post(reverse('member-invite', args=[self.band.id]),
            {'emails': 'new@example.com'}, follow=True)
        self.assertOK(response)

    def test_invite_non_admin(self):
        self.client.force_login(self.joeuser)
        response = self.client.post(reverse('member-invite', args=[self.band.id]),
            {'emails': 'new@example.com'})
        self.assertIsInstance(response, HttpResponseForbidden)

    def test_invite_no_user(self):
        response = self.client.post(reverse('member-invite', args=[self.band.id]),
            {'emails': 'new@example.com'})
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertIn('/accounts/login', response.url)

    def test_invite_redirect_success(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(reverse('member-invite', args=[self.band.id]),
            {'emails': 'new@example.com'})
        self.assertRedirects(response, reverse('band-detail', args=[self.band.id]))

    def test_invite_redirect_error(self):
        self.client.force_login(self.band_admin)
        response = self.client.post(reverse('member-invite', args=[self.band.id]),
            {'emails': 'notanemailaddress'})
        self.assertRedirects(response, reverse('member-invite', args=[self.band.id]))

    def test_invite_delete(self):
        invite = Invite.objects.create(email='new@example.com', band=self.band)
        self.client.force_login(self.band_admin)
        response = self.client.get(reverse('member-invite-delete', args=[invite.id]))
        self.assertRedirects(response, reverse('band-detail', args=[self.band.id]))
        self.assertEqual(Invite.objects.count(), 0)

    def test_invite_delete_own(self):
        invite = Invite.objects.create(email='jane@example.com', band=self.band)
        self.client.force_login(self.janeuser)
        response = self.client.get(reverse('member-invite-delete', args=[invite.id]))
        self.assertRedirects(response, reverse('member-detail', args=[self.janeuser.id]))
        self.assertEqual(Invite.objects.count(), 0)

    def test_invite_delete_super(self):
        invite = Invite.objects.create(email='new@example.com', band=self.band)
        self.client.force_login(self.super)
        response = self.client.get(reverse('member-invite-delete', args=[invite.id]))
        # The band-detail view currently fails if the user has no Assoc, so we
        # can't check if the redirected page actually loads.
        self.assertRedirects(response, reverse('band-detail', args=[self.band.id]),
                             fetch_redirect_response=False)
        self.assertEqual(Invite.objects.count(), 0)

    def test_invite_delete_non_admin(self):
        invite = Invite.objects.create(email='new@example.com', band=self.band)
        self.client.force_login(self.joeuser)
        response = self.client.get(reverse('member-invite-delete', args=[invite.id]))
        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertEqual(Invite.objects.count(), 1)

    def test_invite_delete_no_user(self):
        invite = Invite.objects.create(email='new@example.com', band=self.band)
        response = self.client.get(reverse('member-invite-delete', args=[invite.id]))
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertIn('/accounts/login', response.url)
        self.assertEqual(Invite.objects.count(), 1)

    def test_invite_email(self):
        Invite.objects.create(email='new@example.com', band=self.band)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['new@example.com'])

    @flag_missing_vars
    def test_invite_new_email(self):
        invite = Invite.objects.create(email='new@example.com', band=self.band)
        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Invitation to Join Gig-o-Matic')
        self.assertIn(self.band.name, message.body)
        self.assertIn('get started', message.body)
        self.assertNotIn('existing', message.body)
        self.assertIn(reverse('member-invite-accept', args=[invite.id]), message.body)
        self.assertNotIn(MISSING, message.body)

    @flag_missing_vars
    def test_invite_existing_email(self):
        invite = Invite.objects.create(email=self.janeuser.email, band=self.band)
        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Gig-o-Matic New Band Invite')
        self.assertIn(self.band.name, message.body)
        self.assertNotIn('get started', message.body)
        self.assertIn('existing', message.body)
        self.assertIn(reverse('member-invite-accept', args=[invite.id]), message.body)
        self.assertNotIn(MISSING, message.body)

    @flag_missing_vars
    def test_invite_no_band_email(self):
        invite = Invite.objects.create(email='new@example.com', band=None)
        message = mail.outbox[0]
        self.assertEqual(message.subject, 'Confirm your Email to Join Gig-o-Matic')
        self.assertIn(reverse('member-invite-accept', args=[invite.id]), message.body)
        self.assertNotIn(MISSING, message.body)

    def test_accept_invite_logged_in(self):
        invite = Invite.objects.create(email='jane@example.com', band=self.band)
        self.client.force_login(self.janeuser)
        response = self.client.get(reverse('member-invite-accept', args=[invite.id]))
        self.assertRedirects(response, reverse('member-detail', args=[self.janeuser.id]))
        self.assertEqual(Assoc.objects.filter(band=self.band, member=self.janeuser).count(), 1)
        self.assertEqual(Invite.objects.count(), 0)

    def test_accept_invite_logged_in_no_band(self):
        invite = Invite.objects.create(email='jane@example.com')
        self.client.force_login(self.janeuser)
        response = self.client.get(reverse('member-invite-accept', args=[invite.id]))
        self.assertRedirects(response, reverse('member-detail', args=[self.janeuser.id]))
        self.assertEqual(Assoc.objects.filter(member=self.janeuser).count(), 0)
        self.assertEqual(Invite.objects.count(), 0)

    def test_accept_invite_logged_out(self):
        invite = Invite.objects.create(email='jane@example.com', band=self.band)
        response = self.client.get(reverse('member-invite-accept', args=[invite.id]))
        self.assertOK(response)
        self.assertTemplateUsed(response, 'member/accepted.html')
        self.assertEqual(Assoc.objects.filter(band=self.band, member=self.janeuser).count(), 1)
        self.assertEqual(Invite.objects.count(), 0)

    def test_accept_invite_logged_out_no_band(self):
        invite = Invite.objects.create(email='jane@example.com', band=None)
        response = self.client.get(reverse('member-invite-accept', args=[invite.id]))
        self.assertOK(response)
        self.assertTemplateUsed(response, 'member/accepted.html')
        self.assertEqual(Assoc.objects.filter(member=self.janeuser).count(), 0)
        self.assertEqual(Invite.objects.count(), 0)

    def test_accept_invite_logged_in_other(self):
        n_assoc = Assoc.objects.count()
        invite = Invite.objects.create(email='jane@example.com', band=self.band)
        self.client.force_login(self.joeuser)
        response = self.client.get(reverse('member-invite-accept', args=[invite.id]))
        self.assertOK(response)
        self.assertTemplateUsed(response, 'member/claim_invite.html')
        self.assertIn(b'accept the invite as', response.content)
        self.assertEqual(Invite.objects.count(), 1)  # Didn't delete the invite
        self.assertEqual(Assoc.objects.count(), n_assoc)  # Didn't create an Assoc

    def test_accept_invite_logged_in_other_no_band(self):
        # Note that this is a completely weird state to get into.  This test is merely to
        # check that nothing blows up.
        n_assoc = Assoc.objects.count()
        invite = Invite.objects.create(email='jane@example.com', band=None)
        self.client.force_login(self.joeuser)
        response = self.client.get(reverse('member-invite-accept', args=[invite.id]))
        self.assertOK(response)
        self.assertTemplateUsed(response, 'member/claim_invite.html')
        self.assertIn(b'accept the invite as', response.content)
        self.assertEqual(Invite.objects.count(), 1)  # Didn't delete the invite
        self.assertEqual(Assoc.objects.count(), n_assoc)  # Didn't create an Assoc

    def test_accept_invite_no_member_logged_in(self):
        n_assoc = Assoc.objects.count()
        invite = Invite.objects.create(email='new@example.com', band=self.band)
        self.client.force_login(self.joeuser)
        response = self.client.get(reverse('member-invite-accept', args=[invite.id]))
        self.assertOK(response)
        self.assertTemplateUsed(response, 'member/claim_invite.html')
        self.assertIn(b'create an account for', response.content)
        self.assertEqual(Invite.objects.count(), 1)  # Didn't delete the invite
        self.assertEqual(Assoc.objects.count(), n_assoc)  # Didn't create an Assoc

    def test_accept_invite_no_member_logged_in_no_band(self):
        n_assoc = Assoc.objects.count()
        invite = Invite.objects.create(email='new@example.com', band=None)
        self.client.force_login(self.joeuser)
        response = self.client.get(reverse('member-invite-accept', args=[invite.id]))
        self.assertOK(response)
        self.assertTemplateUsed(response, 'member/claim_invite.html')
        self.assertIn(b'create an account for', response.content)
        self.assertEqual(Invite.objects.count(), 1)  # Didn't delete the invite
        self.assertEqual(Assoc.objects.count(), n_assoc)  # Didn't create an Assoc

    def test_accept_invite_no_member_logged_out(self):
        n_assoc = Assoc.objects.count()
        invite = Invite.objects.create(email='new@example.com', band=self.band)
        response = self.client.get(reverse('member-invite-accept', args=[invite.id]))
        self.assertRedirects(response, reverse('member-create', args=[invite.id]))
        self.assertEqual(Invite.objects.count(), 1)  # Didn't delete the invite
        self.assertEqual(Assoc.objects.count(), n_assoc)  # Didn't create an Assoc

    def test_accept_invite_no_member_logged_out_no_band(self):
        n_assoc = Assoc.objects.count()
        invite = Invite.objects.create(email='new@example.com', band=None)
        response = self.client.get(reverse('member-invite-accept', args=[invite.id]))
        self.assertRedirects(response, reverse('member-create', args=[invite.id]))
        self.assertEqual(Invite.objects.count(), 1)  # Didn't delete the invite
        self.assertEqual(Assoc.objects.count(), n_assoc)  # Didn't create an Assoc

    def test_accept_invite_claim(self):
        invite = Invite.objects.create(email='new@example.com', band=self.band)
        self.client.force_login(self.janeuser)
        response = self.client.get(reverse('member-invite-accept', args=[invite.id]), {'claim': 'true'})
        self.assertRedirects(response, reverse('member-detail', args=[self.janeuser.id]))
        self.assertEqual(Assoc.objects.filter(band=self.band, member=self.janeuser).count(), 1)
        self.assertEqual(Invite.objects.count(), 0)

    def test_accept_invite_duplicate_assoc(self):
        invite = Invite.objects.create(email='joe@example.com', band=self.band)
        self.client.force_login(self.joeuser)
        response = self.client.get(reverse('member-invite-accept', args=[invite.id]), {'claim': 'true'})
        self.assertRedirects(response, reverse('member-detail', args=[self.joeuser.id]))
        self.assertEqual(Assoc.objects.filter(band=self.band, member=self.joeuser).count(), 1)
        self.assertEqual(Invite.objects.count(), 0)

    def test_invite_sets_language(self):
        invite = Invite.objects.create(email='jane@example.com', band=self.band, language='de')
        self.client.get(reverse('member-invite-accept', args=[invite.id]))
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, 'de')

    def test_invite_uses_language(self):
        invite = Invite.objects.create(email='jane@example.com', band=self.band, language='de')
        with self.assertRenderLanguage('de', 'member.views.render'):
            self.client.get(reverse('member-invite-accept', args=[invite.id]))

    def test_invite_sets_language_on_redirect(self):
        invite = Invite.objects.create(email='new@example.com', band=self.band, language='de')
        self.client.get(reverse('member-invite-accept', args=[invite.id]))
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, 'de')

    def test_invite_does_not_override_language(self):
        invite = Invite.objects.create(email='jane@example.com', band=self.band, language='de')
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'en-us'
        self.client.get(reverse('member-invite-accept', args=[invite.id]))
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, 'en-us')

    def test_create_member(self):
        invite = Invite.objects.create(email='new@example.com', band=self.band)
        response = self.client.post(reverse('member-create', args=[invite.id]),
                                    {'username': 'New',
                                     'nickname': 'new',
                                     'password1': self.password,
                                     'password2': self.password})
        # We redirect to the accept invite page, which redirects to the member profile
        self.assertRedirects(response,
                             reverse('member-invite-accept', args=[invite.id]),
                             target_status_code=302)
        new = Member.objects.filter(email='new@example.com').get()
        self.assertEqual(new.username, 'New')
        self.assertEqual(new.nickname, 'new')

    def test_create_member_no_band(self):
        invite = Invite.objects.create(email='new@example.com', band=None)
        response = self.client.post(reverse('member-create', args=[invite.id]),
                                    {'username': 'New',
                                     'nickname': 'new',
                                     'password1': self.password,
                                     'password2': self.password})
        # We redirect to the accept invite page, which redirects to the member profile
        self.assertRedirects(response,
                             reverse('member-invite-accept', args=[invite.id]),
                             target_status_code=302)
        new = Member.objects.filter(email='new@example.com').get()
        self.assertEqual(new.username, 'New')
        self.assertEqual(new.nickname, 'new')

    def test_create_member_full_redirect(self):
        invite = Invite.objects.create(email='new@example.com', band=self.band)
        response = self.client.post(reverse('member-create', args=[invite.id]),
                                    {'username': 'New',
                                     'nickname': 'new',
                                     'password1': self.password,
                                     'password2': self.password},
                                    follow=True)
        self.assertOK(response)
        self.assertTemplateUsed(response, 'member/member_detail.html')

    def test_create_duplicate_member(self):
        invite = Invite.objects.create(email='jane@example.com', band=self.band)
        response = self.client.post(reverse('member-create', args=[invite.id]),
                                    {'username': 'New',
                                     'nickname': 'new',
                                     'password1': self.password,
                                     'password2': self.password})
        self.assertOK(response)
        self.assertIn(b'already exists', response.content)
        self.assertEqual(Member.objects.filter(email='jane@example.com').count(), 1)

    def test_create_bad_password(self):
        invite = Invite.objects.create(email='new@example.com', band=self.band)
        response = self.client.post(reverse('member-create', args=[invite.id]),
                                    {'username': 'New',
                                     'nickname': 'new',
                                     'password1': self.password,
                                     'password2': '54321'})
        self.assertOK(response)
        self.assertIn(b'The two password fields didn\xe2\x80\x99t match.', response.content)
        self.assertEqual(Member.objects.filter(email='new@example.com').count(), 0)

    def test_create_gets_logged_in(self):
        invite = Invite.objects.create(email='new@example.com', band=self.band)
        self.client.post(reverse('member-create', args=[invite.id]),
                         {'username': 'New',
                          'nickname': 'new',
                          'password1': self.password,
                          'password2': self.password})
        self.assertTrue(auth.get_user(self.client).is_authenticated)

    def test_create_gets_invite_language(self):
        invite = Invite.objects.create(email='new@example.com', band=self.band, language="de")
        self.client.post(reverse('member-create', args=[invite.id]),
                         {'username': 'New',
                          'nickname': 'new',
                          'password1': self.password,
                          'password2': self.password})
        new_member = Member.objects.get(email='new@example.com')
        self.assertEqual(new_member.preferences.language, 'de')
        self.assertTrue(auth.get_user(self.client).is_authenticated)

    def test_signup(self):
        response = self.client.post(reverse('member-signup'), {'email': 'new@example.com'})
        self.assertOK(response)
        self.assertEqual(response.json(), {'status': 'success'})
        self.assertEqual(Invite.objects.filter(email='new@example.com', band=None).count(), 1)

    def test_signup_duplicate(self):
        response = self.client.post(reverse('member-signup'), {'email': 'joe@example.com'})
        self.assertOK(response)
        self.assertEqual(response.json(), {'status': 'failure', 'error': 'member exists'})
        self.assertEqual(Invite.objects.filter(email='joe@example.com').count(), 0)

    def test_signup_invalid(self):
        response = self.client.post(reverse('member-signup'), {'email': 'invalid'})
        self.assertOK(response)
        self.assertEqual(response.json(), {'status': 'failure', 'error': 'invalid email'})
        self.assertEqual(Invite.objects.filter(email='invalid').count(), 0)
