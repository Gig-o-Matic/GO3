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

from re import A
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.core import mail
from .models import Band, Assoc, Section
from .helpers import prepare_band_calfeed, band_calfeed, update_band_calfeed, do_delete_assoc
from .util import _get_active_bands, _get_inactive_bands, _get_active_band_members
from member.models import Member
from gig.models import Gig, Plan
from gig.util import GigStatusChoices
from band import helpers
from member.util import MemberStatusChoices
from band.util import AssocStatusChoices
from django.utils import timezone
from datetime import datetime, timedelta
import pytz
from pytz import timezone as pytz_timezone
import json
import os
from django.conf import settings
from pyfakefs.fake_filesystem_unittest import TestCase as FSTestCase
from freezegun import freeze_time
import pytest
from gig.tests import GigTestBase

class MemberTests(TestCase):
    def setUp(self):
        self.super = Member.objects.create_user(
            email='super@b.c', is_superuser=True)
        self.band_admin = Member.objects.create_user(email='admin@e.f')
        self.joeuser = Member.objects.create_user(email='joe@h.i')
        self.janeuser = Member.objects.create_user(email='jane@k.l')
        self.band = Band.objects.create(name='test band')
        Assoc.objects.create(member=self.band_admin, band=self.band,
                             is_admin=True, status=AssocStatusChoices.CONFIRMED)

    def tearDown(self):
        """ make sure we get rid of anything we made """
        Member.objects.all().delete()
        Band.objects.all().delete()
        Assoc.objects.all().delete()

    def assoc_joe(self, status=AssocStatusChoices.CONFIRMED):
        a = Assoc.objects.create(
            member=self.joeuser, band=self.band, status=status)
        return a

    def test_addband(self):

        request = RequestFactory().get(
            '/band/assoc/create/{}/{}'.format(self.band.id, self.joeuser.id))

        # make sure a user can create their own assoc
        request.user = self.joeuser
        helpers.join_assoc(request, bk=self.band.id, mk=self.joeuser.id)

        # make sure a mail is sent to band admin
        self.assertEqual(len(mail.outbox), 1)

        a = Assoc.objects.get(band=self.band, member=self.joeuser)
        a.delete()

        # make sure a superuser can create an assoc for another user
        request.user = self.super
        helpers.join_assoc(request, bk=self.band.id, mk=self.joeuser.id)
        a = Assoc.objects.get(band=self.band, member=self.joeuser)
        a.delete()

        # make sure a band admin can create an assoc for another user for their band
        request.user = self.band_admin

        self.assertEqual(Assoc.objects.count(), 1)
        a = Assoc.objects.get(band=self.band, member=self.band_admin)
        self.assertEqual(a.is_admin, True)

        helpers.join_assoc(request, bk=self.band.id, mk=self.joeuser.id)
        a = Assoc.objects.get(band=self.band, member=self.joeuser)
        a.delete()

        # make sure nobody else can
        request.user = self.janeuser
        with self.assertRaises(PermissionError):
            helpers.join_assoc(request, bk=self.band.id, mk=self.joeuser.id)

        # make sure we can't have two assocs to the same band
        request.user = self.band_admin
        helpers.join_assoc(request, bk=self.band.id, mk=self.joeuser.id)
        helpers.join_assoc(request, bk=self.band.id, mk=self.joeuser.id)
        self.assertEqual(len(Assoc.objects.filter(
            band=self.band, member=self.joeuser)), 1)


    def test_deleting_section(self):

        # be sure we're a member of the default section
        assoc = Assoc.objects.get(band=self.band, member=self.band_admin)
        self.assertTrue(assoc.default_section.is_default)

        # make a new section
        new_section = Section.objects.create(band=self.band, name="foohorn")
        assoc.default_section = new_section
        assoc.save()

        # be sure we're now not a member of the default section
        assoc = Assoc.objects.get(band=self.band, member=self.band_admin)
        self.assertFalse(assoc.default_section.is_default)
        self.assertEqual(assoc.default_section.name, "foohorn")
        self.assertEqual(assoc.default_section, new_section)

        # now delete the new section and see that we've reverted back to the old section
        new_section.delete()
        assoc = Assoc.objects.get(band=self.band, member=self.band_admin)
        self.assertTrue(assoc.default_section.is_default)
        self.assertEqual(assoc.default_section,
                         self.band.sections.get(is_default=True))

    def test_populated_default(self):
        """ if the default section is empty, don't return it from Band.sections.populated() """
        # be sure we're a member of the default section
        assoc = Assoc.objects.get(band=self.band, member=self.band_admin)
        self.assertTrue(assoc.default_section.is_default)

        # make a new section
        new_section = Section.objects.create(band=self.band, name="foohorn")
        self.assertFalse(new_section.is_default)

        self.assertEqual(len(self.band.sections.all()), 2)
        self.assertEqual(len(self.band.sections.populated()), 2)

        # now change all assocs to be in the new section
        all = Assoc.objects.filter(band=self.band)
        for a in all:
            a.default_section = new_section
            a.save()

        # now show that the populated sections don't include the default
        self.assertEqual(len(self.band.sections.populated()), 1)

    def test_tf_param_user(self):
        a = self.assoc_joe()
        self.client.force_login(self.joeuser)
        resp = self.client.post(
            reverse('assoc-tfparam', args=[a.id]), {'is_occasional': 'true'})
        self.assertEqual(resp.status_code, 204)
        a.refresh_from_db()
        self.assertEqual(a.is_occasional, True)

    def test_tf_param_admin(self):
        a = self.assoc_joe()
        self.client.force_login(self.band_admin)
        resp = self.client.post(
            reverse('assoc-tfparam', args=[a.id]), {'is_occasional': 'true'})
        self.assertEqual(resp.status_code, 204)
        a.refresh_from_db()
        self.assertEqual(a.is_occasional, True)

    def test_tf_param_other(self):
        a = self.assoc_joe()
        self.client.force_login(self.janeuser)
        resp = self.client.post(
            reverse('assoc-tfparam', args=[a.id]), {'is_occasional': 'true'})
        self.assertEqual(resp.status_code, 403)
        a.refresh_from_db()
        self.assertEqual(a.is_occasional, False)

    def test_tf_param_is_admin_user(self):
        a = self.assoc_joe()
        self.client.force_login(self.joeuser)
        resp = self.client.post(
            reverse('assoc-tfparam', args=[a.id]), {'is_admin': 'true'})
        self.assertEqual(resp.status_code, 204)
        a.refresh_from_db()
        self.assertEqual(a.is_admin, False)

    def test_tf_param_is_admin_admin(self):
        a = self.assoc_joe()
        self.client.force_login(self.band_admin)
        resp = self.client.post(
            reverse('assoc-tfparam', args=[a.id]), {'is_admin': 'true'})
        self.assertEqual(resp.status_code, 204)
        a.refresh_from_db()
        self.assertEqual(a.is_admin, True)

    def test_tf_param_is_admin_other(self):
        a = self.assoc_joe()
        self.client.force_login(self.janeuser)
        resp = self.client.post(
            reverse('assoc-tfparam', args=[a.id]), {'is_admin': 'true'})
        self.assertEqual(resp.status_code, 403)
        a.refresh_from_db()
        self.assertEqual(a.is_admin, False)

    def test_section_user(self):
        a = self.assoc_joe()
        s = Section.objects.create(band=a.band)
        self.client.force_login(self.joeuser)
        resp = self.client.post(reverse('assoc-section', args=[a.id, s.id]))
        self.assertEqual(resp.status_code, 204)
        a.refresh_from_db()
        self.assertEqual(a.section, s)

    def test_section_admin(self):
        a = self.assoc_joe()
        s = Section.objects.create(band=a.band)
        self.client.force_login(self.band_admin)
        resp = self.client.post(reverse('assoc-section', args=[a.id, s.id]))
        self.assertEqual(resp.status_code, 204)
        a.refresh_from_db()
        self.assertEqual(a.section, s)

    def test_section_other(self):
        a = self.assoc_joe()
        s0 = a.section
        s = Section.objects.create(band=a.band)
        self.client.force_login(self.janeuser)
        resp = self.client.post(reverse('assoc-section', args=[a.id, s.id]))
        self.assertEqual(resp.status_code, 403)
        a.refresh_from_db()
        self.assertEqual(a.section, s0)

    def test_section_other_band(self):
        a = self.assoc_joe()
        s0 = a.section
        b = Band.objects.create(name='Other Band')
        s = Section.objects.create(band=b)
        self.client.force_login(self.joeuser)
        resp = self.client.post(reverse('assoc-section', args=[a.id, s.id]))
        self.assertEqual(resp.status_code, 404)
        a.refresh_from_db()
        self.assertEqual(a.section, s0)

    def test_color_user(self):
        a = self.assoc_joe()
        self.client.force_login(self.joeuser)
        resp = self.client.post(reverse('assoc-color', args=[a.id, 2]))
        self.assertEqual(resp.status_code, 200)
        a.refresh_from_db()
        self.assertEqual(a.color, 2)

    def test_color_admin(self):
        # This is a bit odd, and there's no UI set up to allow this, but it makes
        # the implementation easy.
        a = self.assoc_joe()
        self.client.force_login(self.band_admin)
        resp = self.client.post(reverse('assoc-color', args=[a.id, 2]))
        self.assertEqual(resp.status_code, 200)
        a.refresh_from_db()
        self.assertEqual(a.color, 2)

    def test_color_other(self):
        a = self.assoc_joe()
        self.client.force_login(self.janeuser)
        resp = self.client.post(reverse('assoc-color', args=[a.id, 2]))
        self.assertEqual(resp.status_code, 403)
        a.refresh_from_db()
        self.assertEqual(a.color, 0)

    def test_delete_user(self):
        a = self.assoc_joe()
        self.client.force_login(self.joeuser)
        resp = self.client.post(reverse('assoc-delete', args=[a.id]))
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Assoc.objects.filter(member=self.joeuser).count(), 1)
        self.assertEqual(Assoc.objects.filter(member=self.joeuser).first().status, AssocStatusChoices.NOT_CONFIRMED)

    def test_delete_admin(self):
        a = self.assoc_joe()
        self.client.force_login(self.band_admin)
        resp = self.client.post(reverse('assoc-delete', args=[a.id]))
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Assoc.objects.filter(member=self.joeuser).count(), 1)
        self.assertEqual(Assoc.objects.filter(member=self.joeuser).first().status, AssocStatusChoices.NOT_CONFIRMED)

    def test_delete_other(self):
        a = self.assoc_joe()
        self.client.force_login(self.janeuser)
        resp = self.client.post(reverse('assoc-delete', args=[a.id]))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Assoc.objects.filter(member=self.joeuser).count(), 1)

    def test_confirm_user(self):
        a = self.assoc_joe(AssocStatusChoices.PENDING)
        self.client.force_login(self.joeuser)
        resp = self.client.post(reverse('assoc-confirm', args=[a.id]))
        self.assertEqual(resp.status_code, 403)
        a.refresh_from_db()
        self.assertEqual(a.status, AssocStatusChoices.PENDING)

    def test_confirm_admin(self):
        a = self.assoc_joe(AssocStatusChoices.PENDING)
        self.client.force_login(self.band_admin)
        resp = self.client.post(reverse('assoc-confirm', args=[a.id]))
        self.assertEqual(resp.status_code, 200)
        a.refresh_from_db()
        self.assertEqual(a.status, AssocStatusChoices.CONFIRMED)

    def test_confirm_other(self):
        a = self.assoc_joe(AssocStatusChoices.PENDING)
        self.client.force_login(self.janeuser)
        resp = self.client.post(reverse('assoc-confirm', args=[a.id]))
        self.assertEqual(resp.status_code, 403)
        a.refresh_from_db()
        self.assertEqual(a.status, AssocStatusChoices.PENDING)

    def test_alum_flag(self):
        a = self.assoc_joe(AssocStatusChoices.PENDING)
        self.assertFalse(a.is_alum)
        a.status = AssocStatusChoices.CONFIRMED
        a.save()
        self.assertTrue(a.is_alum)
        a.status = AssocStatusChoices.NOT_CONFIRMED
        a.save()
        self.assertTrue(a.is_alum)

    def test_revert_alum_status(self):
        a = self.assoc_joe(AssocStatusChoices.CONFIRMED)
        a.is_alum = True
        a.save()
        self.assertIsNotNone(do_delete_assoc(a))
        self.assertEqual(a.status, AssocStatusChoices.NOT_CONFIRMED)
        a.is_alum = False
        a.save()
        self.assertIsNone(do_delete_assoc(a))

class BandTests(GigTestBase):
    def test_condensed_name(self):
        b1 = Band.objects.create(name="condense test")
        self.assertEqual(b1.condensed_name, "condensetest")

        # fire the signal again but make sure it doesn't affect anything
        b1.save()
        self.assertEqual(b1.condensed_name, "condensetest")

        b2 = Band.objects.create(name="condense test")
        self.assertNotEqual(b2.condensed_name, b1.condensed_name)
        self.assertEqual(b2.condensed_name, "condensetest1")

        # fire the signal again but make sure it doesn't affect anything
        b2.save()
        self.assertEqual(b2.condensed_name, "condensetest1")

        # make sure we're only using ascii characters, too
        b3 = Band.objects.create(name="fünny çharacters😀")
        self.assertEqual(b3.condensed_name, "funnycharacters")


    def test_edit_permissions(self):
        self.assertTrue(self.band.is_editor(self.band_admin))
        self.assertFalse(self.band.is_editor(self.joeuser))

    def test_band_member_queries(self):
        self.assertEqual(self.band.all_assocs.count(), 1)
        self.assertEqual(self.band.confirmed_assocs.count(), 1)
        a = Assoc.objects.create(
            member=self.joeuser, band=self.band, is_admin=False)
        self.assertEqual(self.band.all_assocs.count(), 2)
        self.assertEqual(self.band.confirmed_assocs.count(), 1)
        a.status = AssocStatusChoices.CONFIRMED
        a.save()
        self.assertEqual(self.band.confirmed_assocs.count(), 2)
        self.joeuser.status = MemberStatusChoices.DORMANT
        self.joeuser.save()
        self.assertEqual(self.band.all_assocs.count(), 1)
        self.assertEqual(self.band.confirmed_assocs.count(), 1)

    def test_trashed_gigs(self):
        g = self.create_gig(self.joeuser)
        self.assertEqual(self.band.gigs.count(), 1)
        self.assertEqual(self.band.gigs.active().count(), 1)
        self.assertEqual(self.band.trash_gigs.count(), 0)
        g.trashed_date = timezone.now()
        g.save()
        self.assertEqual(self.band.gigs.all().count(), 1)
        self.assertEqual(self.band.gigs.active().count(), 0)
        self.assertEqual(self.band.gigs.trashed().count(), 1)

    def test_trashcan_permission(self):
        _, a, _ = self.assoc_joe_and_create_gig()
        self.client.force_login(self.janeuser)
        resp = self.client.get(reverse('band-trashcan', args=[a.band.id]))
        self.assertEqual(resp.status_code, 403)

        self.client.force_login(self.joeuser)
        resp = self.client.get(reverse('band-trashcan', args=[a.band.id]))
        self.assertEqual(resp.status_code, 200)

    def test_archive_permission(self):
        _, a, _ = self.assoc_joe_and_create_gig()
        self.client.force_login(self.janeuser)
        resp = self.client.get(reverse('band-archive', args=[a.band.id]))
        self.assertEqual(resp.status_code, 403)

        self.client.force_login(self.joeuser)
        resp = self.client.get(reverse('band-archive', args=[a.band.id]))
        self.assertEqual(resp.status_code, 200)

    def test_archive_download_permission(self):
        _, a, _ = self.assoc_joe_and_create_gig()
        self.client.force_login(self.janeuser)
        resp = self.client.get(reverse('archive-spreadsheet', args=[a.band.id]))
        self.assertEqual(resp.status_code, 403)

        self.client.force_login(self.joeuser)
        resp = self.client.get(reverse('archive-spreadsheet', args=[a.band.id]))
        self.assertEqual(resp.status_code, 200)


    def test_section_setup_permission(self):
        _, a, _ = self.assoc_joe_and_create_gig()
        self.client.force_login(self.janeuser)
        resp = self.client.post(reverse('band-set-sections', args=[a.band.id]),
                                data={
            'sectionInfo': [['hey', '', 'hey']],
            'deletedSections': []
        }
        )
        self.assertEqual(resp.status_code, 403)

    def test_section_setup(self):
        _, a, _ = self.assoc_joe_and_create_gig()
        # starts with default section
        self.assertEqual(self.band.sections.count(), 1)
        self.client.force_login(self.band_admin)

        # test creation
        resp = self.client.post(reverse('band-set-sections', args=[a.band.id]),
                                data={
            'sectionInfo': json.dumps([['hey', '', 'hey']]),
            'deletedSections': json.dumps([])
        }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.band.sections.count(), 2)
        secs = self.band.sections.filter(is_default=False)
        self.assertEqual(secs.count(), 1)
        sec = secs.first()
        self.assertEqual(sec.name, 'hey')

        # test rename
        resp = self.client.post(reverse('band-set-sections', args=[a.band.id]),
                                data={
            'sectionInfo': json.dumps([['whoa', sec.id, 'hey']]),
            'deletedSections': json.dumps([])
        }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.band.sections.count(), 2)
        secs = self.band.sections.filter(is_default=False)
        self.assertEqual(secs.count(), 1)
        sec = secs.first()
        self.assertEqual(sec.name, 'whoa')

        # test delete
        resp = self.client.post(reverse('band-set-sections', args=[a.band.id]),
                                data={
            'sectionInfo': json.dumps([]),
            'deletedSections': json.dumps([sec.id])
        }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.band.sections.count(), 1)
        self.assertTrue(self.band.sections.first().is_default)

        # test reorder
        resp = self.client.post(reverse('band-set-sections', args=[a.band.id]),
                                data={
            'sectionInfo': json.dumps([['hey', '', 'hey'], ['foo', '', 'foo']]),
            'deletedSections': json.dumps([])
        }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.band.sections.count(), 3)
        secs = self.band.sections.filter(is_default=False)
        self.assertEqual(secs.count(), 2)
        sec1 = secs.first()
        self.assertEqual(sec1.name, 'hey')
        self.assertEqual(sec1.order, 0)

        sec2 = secs.last()
        self.assertEqual(sec2.name, 'foo')
        self.assertEqual(sec2.order, 1)

        resp = self.client.post(reverse('band-set-sections', args=[a.band.id]),
                                data={
            'sectionInfo': json.dumps([['foo', sec2.id, 'foo'], ['hey', sec1.id, 'hey']]),
            'deletedSections': json.dumps([])
        }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.band.sections.count(), 3)
        secs = self.band.sections.filter(is_default=False)
        self.assertEqual(secs.count(), 2)
        sec1 = secs.first()
        self.assertEqual(sec1.name, 'foo')
        self.assertEqual(sec1.order, 0)

        # make sure we can't delete the default section
        defsecs = self.band.sections.filter(is_default=True)
        self.assertEqual(defsecs.count(), 1)
        defsec = defsecs.first()
        resp = self.client.post(reverse('band-set-sections', args=[a.band.id]),
                                data={
            'sectionInfo': json.dumps([['foo', sec2.id, 'foo'], ['hey', sec1.id, 'hey']]),
            'deletedSections': json.dumps([defsec.id])
        }
        )
        self.assertEqual(self.band.sections.count(), 3)
        defsecs = self.band.sections.filter(is_default=True)
        self.assertEqual(defsecs.count(), 1)
        self.assertEqual(defsec.id, defsecs.first().id)

    def test_delete_band(self):
        # set up some sections in the band
        section1 = Section.objects.create(
            name='section a', order=1, band=self.band, is_default=False)
        section2 = Section.objects.create(
            name='section b', order=2, band=self.band, is_default=False)

        g, a1, _ = self.assoc_joe_and_create_gig()
        a1.default_section = section1
        a1.save()

        a2 = Assoc.objects.create(
            member=self.janeuser, band=self.band, status=AssocStatusChoices.CONFIRMED)
        a2.default_section = section2
        a2.save()

        # at this point, we should have one band, three sections, three assocs, three plans
        self.assertEqual(Band.objects.count(), 1)
        self.assertEqual(Section.objects.count(), 3)
        self.assertEqual(Assoc.objects.count(), 3)
        self.assertEqual(g.member_plans.count(), 3)

        self.band.delete()
        # should be no bands, no sections, no assocs, no member plans
        self.assertEqual(Band.objects.count(), 0)
        self.assertEqual(Section.objects.count(), 0)
        self.assertEqual(Assoc.objects.count(), 0)
        self.assertEqual(Gig.objects.count(), 0)
        self.assertEqual(Plan.objects.count(), 0)

    def test_delete_assoc(self):
        # when we delete an assoc using the helper function, it should actually keep the assoc
        # but change the status to ALUMNI. Future plans
        # should be deleted but old plans should stay around.
        g1, a1, _ = self.assoc_joe_and_create_gig()
        g1.date=g1.date.replace(year=2020)
        g1.save()
        plans = g1.plans.filter(assoc__member=self.joeuser)
        self.assertEqual(plans.count(),1)
        self.assertEqual(plans.first().gig.date.year,2020)

        g2 = self.create_gig_form() # make another gig
        plans = g2.plans.filter(assoc__member=self.joeuser)
        self.assertEqual(plans.count(),1)

        # now delete the assoc and show the the plan now belongs to an alumni
        self.client.force_login(self.joeuser)
        resp = self.client.post(reverse('assoc-delete', args=[a1.id]))
        self.assertEqual(resp.status_code, 204)

        plans = g1.plans.exclude(assoc__member=self.band_admin)
        self.assertEqual(plans.count(),1)
        self.assertEqual(plans.first().assoc.status, AssocStatusChoices.NOT_CONFIRMED)

        # make sure the future gig plan got deleted
        plans = g2.plans.filter(assoc__member=self.joeuser)
        self.assertEqual(plans.count(),0) # future plan should be gone


    def test_delete_assoc_multiband(self):
        band1 = self.band
        a1 = Assoc.objects.create(
            member=self.joeuser, band=band1, status=AssocStatusChoices.CONFIRMED
        )
        g1 = self.create_gig_form(contact=self.joeuser)
        p1 = g1.member_plans.filter(assoc=a1).get()
        self.assertIsNotNone(p1)

        band2 = Band.objects.create(
                name="test band 2",
                timezone="UTC",
                anyone_can_create_gigs=True,
                hometown="Seattle",
            )
        a2 = Assoc.objects.create(
            member=self.joeuser, band=band2, status=AssocStatusChoices.CONFIRMED
        )
        g2 = self.create_gig_form(contact=self.joeuser, band=band2)
        p2 = g2.member_plans.filter(assoc=a2).get()
        self.assertIsNotNone(p2)

        # now delete the assoc for band 1
        self.client.force_login(self.joeuser)
        resp = self.client.post(reverse('assoc-delete', args=[a1.id]))
        self.assertEqual(resp.status_code, 204)

        # make sure the future gig plan got deleted
        plans = g1.plans.filter(assoc__member=self.joeuser)
        self.assertEqual(plans.count(),0) # future plan should be gone

        # now show that we still have a plan for the other band
        plans = g2.plans.filter(assoc__member=self.joeuser)
        self.assertEqual(plans.count(),1) # future plan should be gone

class SectionTest(TestCase):
    def test_auto_assign_section_order(self):
        band = Band.objects.create(name="Example")
        section1 = band.sections.create(name="Section 1")
        section2 = band.sections.create(name="Section 2")
        self.assertGreater(section2.order, section1.order)

class PublicBandPageTest(GigTestBase):
    def test_public_gigs(self):
        band = self.band
        Assoc.objects.create(
            member=self.joeuser, band=band, status=AssocStatusChoices.CONFIRMED
        )
        self.create_gig_form(contact=self.joeuser, title="test1")
        self.create_gig_form(contact=self.joeuser, title="test2", is_private=True)
        self.create_gig_form(contact=self.joeuser, title="test3")

        response = self.client.post(reverse('band-public-gigs', args=[band.id]))
        content = response.content.decode("ascii")
        self.assertTrue("test1" in content)
        self.assertFalse("test2" in content)
        self.assertTrue("test3" in content)

        otherband = Band.objects.create(name='other band')
        Assoc.objects.create(member=self.joeuser,
                             band=otherband, is_admin=True, status=AssocStatusChoices.CONFIRMED)
        self.create_gig_form(contact=self.joeuser, title="other band gig", band=otherband)

        response = self.client.post(reverse('band-public-gigs', args=[band.id]))
        content = response.content.decode("ascii")
        self.assertFalse("other band gig" in content)

    def test_public_page_access(self):
        """ the public page should be accessible to everyone. The band detail """
        """ page should only be accessible to members """

        _, a, _ = self.assoc_joe_and_create_gig()
        self.client.force_login(self.joeuser)

        resp = self.client.get(
            reverse('band-detail', args=[self.band.id]))
        self.assertEqual(resp.status_code, 200)

        a.status = AssocStatusChoices.NOT_CONFIRMED
        a.save()
        resp = self.client.get(
            reverse('band-detail', args=[self.band.id]))
        # if a logged-in person tries to access a band they're not a member of, they should
        # be redirected to the band's public page
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, f'/band/pub/{self.band.condensed_name}/')

        otherband = Band.objects.create(name='other band')
        resp = self.client.get(
            reverse('band-detail', args=[otherband.id]))
        # if a logged-in person tries to access a band they're not a member of, they should
        # be redirected to the band's public page
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, f'/band/pub/{otherband.condensed_name}/')

        resp = self.client.get(
            reverse('band-public-page', args=[otherband.condensed_name]))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(
            reverse('band-public-page', args=["xyzzy"]))
        self.assertEqual(resp.status_code, 404)

        resp = self.client.get(reverse('logout'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/accounts/login')

        # logged out, test again
        resp = self.client.get(
            reverse('band-detail', args=[self.band.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, f'/accounts/login/?next=/band/{self.band.id}/')

        resp = self.client.get(
            reverse('band-detail', args=[otherband.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, f'/accounts/login/?next=/band/{otherband.id}/')

        resp = self.client.get(
            reverse('band-public-page', args=[otherband.condensed_name]))
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(
            reverse('band-public-page', args=["xyzzy"]))
        self.assertEqual(resp.status_code, 404)

@pytest.mark.django_db
class BandCalfeedTest(FSTestCase):
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
        self.create_gigs()

    def tearDown(self):
        """ make sure we get rid of anything we made """
        Member.objects.all().delete()
        Band.objects.all().delete()
        Assoc.objects.all().delete()
        Gig.objects.all().delete()

    def create_gigs(self):
        the_date = timezone.datetime(
            2100, 1, 2, tzinfo=pytz.timezone(self.band.timezone))
        Gig.objects.create(
            title="Good Gig",
            band_id=self.band.id,
            date=the_date,
            setdate=the_date + timedelta(minutes=30),
            enddate=the_date + timedelta(hours=2),
            status=GigStatusChoices.CONFIRMED
        )
        Gig.objects.create(
            title="Private Gig",
            band_id=self.band.id,
            date=the_date,
            setdate=the_date + timedelta(minutes=30),
            enddate=the_date + timedelta(hours=2),
            is_private=True,
            status=GigStatusChoices.CONFIRMED
        )
        Gig.objects.create(
            title="Canceled Gig",
            band_id=self.band.id,
            date=the_date,
            setdate=the_date + timedelta(minutes=30),
            enddate=the_date + timedelta(hours=2),
            status=GigStatusChoices.CANCELED
        )
        Gig.objects.create(
            title="Trashed Gig",
            band_id=self.band.id,
            date=the_date,
            setdate=the_date + timedelta(minutes=30),
            enddate=the_date + timedelta(hours=2),
            status=GigStatusChoices.CONFIRMED,
            trashed_date=datetime.now(pytz_timezone('UTC')),
        )
        Gig.objects.create(
            title="Archived Gig",
            band_id=self.band.id,
            date=the_date,
            setdate=the_date + timedelta(minutes=30),
            enddate=the_date + timedelta(hours=2),
            status=GigStatusChoices.CONFIRMED,
            is_archived=True,
        )

    def test_band_caldav_stream(self):
        cf = prepare_band_calfeed(self.band)
        self.assertTrue(cf.find(b'Good Gig') >= 0)
        self.assertTrue(cf.find(b'Private Gig') < 0)
        self.assertTrue(cf.find(b'Canceled Gig') < 0)
        self.assertTrue(cf.find(b'Trashed Gig') < 0)
        self.assertTrue(cf.find(b'Archived Gig') >= 0)

    def test_member_calfeed_bad_url(self):
        """ fail on bad calfeed url """
        self.setUpPyfakefs()    # fake a file system
        os.mkdir('calfeeds')

        # should fail due to bad calfeed id
        r = band_calfeed(request=None, pk='xyz')
        self.assertEqual(r.status_code, 404)

    def test_band_calfeed_url(self):
        """ fake a file system """
        self.setUpPyfakefs()    # fake a file system
        os.mkdir('calfeeds')

        # turn on dynamic calfeeds - worry about the queue version some other time
        settings.DYNAMIC_CALFEED = True

        self.band.pub_cal_feed_dirty = True
        self.band.save()
        update_band_calfeed(self.band.id)
        self.band.refresh_from_db()
        # self.assertFalse(self.band.pub_cal_feed_dirty) # moved this to an async task

        cf = band_calfeed(request=None, pk=self.band.pub_cal_feed_id)
        self.assertTrue(cf.content.decode('ascii').find('EVENT') > 0)

    def test_band_calfeeds_dirty(self):
        self.band.pub_cal_feed_dirty = False
        self.band.save()

        g = Gig.objects.first()
        g.title = "Edited"
        g.save()
        self.band.refresh_from_db()
        self.assertTrue(self.band.pub_cal_feed_dirty)

class ActiveBandTests(TestCase):
    def test_active_band_list(self):

        def _make_gig(band, title, days_ago):
            with freeze_time(datetime.now(pytz_timezone('UTC')) - timedelta(days=days_ago)):
                Gig.objects.create(band=band, title=title, date=datetime.now(pytz_timezone('UTC')))

        b1 = Band.objects.create(name='testband1')
        b2 = Band.objects.create(name='testband2')
        b3 = Band.objects.create(name='testband3')

        # first, should get no bands because there are no gigs
        list = _get_active_bands()
        self.assertTrue(len(list)==0)

        # make a gig for a band
        _make_gig(b1,"test1",1)
        list=_get_active_bands()
        self.assertEqual(len(list), 1)
        self.assertEqual(list[0], b1)

        # now create a gig for a second band
        _make_gig(b2,"test2",2)
        list=_get_active_bands()
        self.assertEqual(len(list), 2)
        self.assertTrue(b1 in list)
        self.assertTrue(b2 in list)

        # now create a gig in the distant past for a third band
        _make_gig(b3,"test3",31)
        list=_get_active_bands()
        self.assertEqual(len(list), 2)
        self.assertTrue(b1 in list)
        self.assertTrue(b2 in list)
        self.assertFalse(b3 in list)

        # now wake the third band up
        _make_gig(b3,"test4",29)
        list=_get_active_bands()
        self.assertEqual(len(list), 3)
        self.assertTrue(b1 in list)
        self.assertTrue(b2 in list)
        self.assertTrue(b3 in list)

        # now: test that a band that created its last gig more than 30 days ago BUT has gigs in the future is
        # noted as still being active

        Gig.objects.all().delete()

        with freeze_time(datetime.now(pytz_timezone('UTC')) - timedelta(days=60)):
            Gig.objects.create(band=b1, title="future past1", date=datetime.now(pytz_timezone('UTC'))+timedelta(days=100))
            Gig.objects.create(band=b2, title="future past2", date=datetime.now(pytz_timezone('UTC')))
        Gig.objects.create(band=b3, title="future past3", date=datetime.now(pytz_timezone('UTC')))

        list=_get_active_bands()
        self.assertEqual(len(list), 2)
        self.assertTrue(b1 in list)
        self.assertTrue(b2 not in list)
        self.assertTrue(b3 in list)

        # add another gig and make sure each band only shows up once
        Gig.objects.create(band=b3, title="future past3", date=datetime.now(pytz_timezone('UTC')))
        list=_get_active_bands()
        self.assertEqual(len(list), 2)
        self.assertTrue(b1 in list)
        self.assertTrue(b2 not in list)
        self.assertTrue(b3 in list)

    def test_inactive_band_list(self):

        def _make_gig(band, title, days_ago):
            with freeze_time(datetime.now(pytz_timezone('UTC')) - timedelta(days=days_ago)):
                Gig.objects.create(band=band, title=title, date=datetime.now(pytz_timezone('UTC')))

        b1 = Band.objects.create(name='testband1')
        b2 = Band.objects.create(name='testband2')
        b3 = Band.objects.create(name='testband3')

        # first, should get no bands because there are no gigs
        list = _get_inactive_bands()
        self.assertTrue(len(list)==3)
        self.assertTrue(b1 in list)
        self.assertTrue(b2 in list)
        self.assertTrue(b3 in list)

        # make a gig for a band
        _make_gig(b1,"test1",1)
        list=_get_inactive_bands()
        self.assertEqual(len(list), 2)
        self.assertTrue(b1 not in list)
        self.assertTrue(b2 in list)
        self.assertTrue(b3 in list)

        # now create a gig for a second band
        _make_gig(b2,"test2",2)
        list=_get_inactive_bands()
        self.assertEqual(len(list), 1)
        self.assertTrue(b1 not in list)
        self.assertTrue(b2 not in list)
        self.assertTrue(b3 in list)

        # now create a gig in the distant past for a third band
        _make_gig(b3,"test3",31)
        list=_get_inactive_bands()
        self.assertEqual(len(list), 1)
        self.assertTrue(b1 not in list)
        self.assertTrue(b2 not in list)
        self.assertTrue(b3 in list)

        # now wake the third band up
        _make_gig(b3,"test4",29)
        list=_get_inactive_bands()
        self.assertEqual(len(list), 0)

        # now: test that a band that created its last gig more than 30 days ago BUT has gigs in the future is
        # not noted as being in active

        Gig.objects.all().delete()

        with freeze_time(datetime.now(pytz_timezone('UTC')) - timedelta(days=60)):
            # 60 days ago a band makes a gig 100 days in the future
            Gig.objects.create(band=b1, title="future past", date=datetime.now(pytz_timezone('UTC'))+timedelta(days=100))
            # 60 days ago a band makes a gig 60 days ago
            Gig.objects.create(band=b2, title="future past2", date=datetime.now(pytz_timezone('UTC')))
        # now, a band makes a gig now
        Gig.objects.create(band=b3, title="future past3", date=datetime.now(pytz_timezone('UTC')))

        list=_get_inactive_bands()
        self.assertEqual(len(list), 1)
        self.assertTrue(b1 not in list)
        self.assertTrue(b2 in list)
        self.assertTrue(b3 not in list)

    def test_active_members(self):
        # set up an active band and an inactive band
        b1 = Band.objects.create(name='testband1')
        b2 = Band.objects.create(name='testband2')

        with freeze_time(datetime.now(pytz_timezone('UTC')) - timedelta(days=60)):
            # active band
            Gig.objects.create(band=b1, title="future past", date=datetime.now(pytz_timezone('UTC'))+timedelta(days=100))
            # inactive band
            Gig.objects.create(band=b2, title="future past2", date=datetime.now(pytz_timezone('UTC')))

        list=_get_active_bands()
        self.assertEqual(len(list), 1)
        self.assertTrue(b1 in list)
        self.assertTrue(b2 not in list)

        # now make some members
        m1 = Member.objects.create_user(email='1@h.i')
        m2 = Member.objects.create_user(email='2@h.i')
        m3 = Member.objects.create_user(email='3@h.i')

        # join the bands
        Assoc.objects.create(band=b1, member=m1, status=AssocStatusChoices.CONFIRMED)
        Assoc.objects.create(band=b2, member=m2, status=AssocStatusChoices.CONFIRMED)
        Assoc.objects.create(band=b1, member=m3, status=AssocStatusChoices.CONFIRMED)
        Assoc.objects.create(band=b2, member=m3, status=AssocStatusChoices.CONFIRMED)

        list = _get_active_band_members()
        self.assertEqual(len(list), 2)
        self.assertTrue(m1 in list)
        self.assertTrue(m2 not in list)
        self.assertTrue(m3 in list)

        # add another inactive band
        b3 = Band.objects.create(name='testband2')
        Assoc.objects.create(band=b3, member=m1, status=AssocStatusChoices.CONFIRMED)
        list = _get_active_band_members()
        self.assertEqual(len(list), 2)
        self.assertTrue(m1 in list)
        self.assertTrue(m2 not in list)
        self.assertTrue(m3 in list)

        # now make it active
        Gig.objects.create(band=b3, title="future past3", date=datetime.now(pytz_timezone('UTC')))
        list = _get_active_band_members()
        self.assertEqual(len(list), 2)
        self.assertTrue(m1 in list)
        self.assertTrue(m2 not in list)
        self.assertTrue(m3 in list)
