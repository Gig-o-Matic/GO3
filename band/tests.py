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

from django.test import TestCase, RequestFactory
from .models import Band, Assoc, Section
from member.models import Member
from band import helpers
from member.util import MemberStatusChoices
from band.util import AssocStatusChoices

class MemberTests(TestCase):
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


    def test_addband(self):

        request = RequestFactory().get('/band/assoc/create/{}/{}'.format(self.band.id, self.joeuser.id))

        # make sure a user can create their own assoc
        request.user = self.joeuser
        helpers.join_assoc(request, bk=self.band.id, mk=self.joeuser.id)
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
        self.assertEqual(len(Assoc.objects.filter(band=self.band, member=self.joeuser)), 1)


    def test_leaveband(self):
        request = RequestFactory().get('/band/assoc/{}/delete'.format(self.joeuser.id))

        # make sure a user can delete their own assoc
        request.user = self.joeuser
        self.assertEqual(Assoc.objects.filter(band=self.band, member=self.joeuser).count(),0)
        a = Assoc.objects.create(band=self.band, member=self.joeuser)
        self.assertEqual(Assoc.objects.filter(band=self.band, member=self.joeuser).count(),1)
        helpers.delete_assoc(request, ak=a.id)
        self.assertEqual(Assoc.objects.filter(band=self.band, member=self.joeuser).count(),0)

        # make sure a superuser can delete an assoc
        request.user = self.super
        a = Assoc.objects.create(band=self.band, member=self.joeuser)
        self.assertEqual(Assoc.objects.filter(band=self.band, member=self.joeuser).count(),1)
        helpers.delete_assoc(request, ak=a.id)
        self.assertEqual(Assoc.objects.filter(band=self.band, member=self.joeuser).count(),0)

        # make sure a band_admin can delete an assoc
        request.user = self.band_admin
        a = Assoc.objects.create(band=self.band, member=self.joeuser)
        self.assertEqual(Assoc.objects.filter(band=self.band, member=self.joeuser).count(),1)
        helpers.delete_assoc(request, ak=a.id)
        self.assertEqual(Assoc.objects.filter(band=self.band, member=self.joeuser).count(),0)

        # make sure nobody else can delete an assoc
        request.user = self.janeuser
        a = Assoc.objects.create(band=self.band, member=self.joeuser)
        self.assertEqual(Assoc.objects.filter(band=self.band, member=self.joeuser).count(),1)
        with self.assertRaises(PermissionError):
            helpers.delete_assoc(request, ak=a.id)


    def test_confirmband(self):
        request = RequestFactory().get('/band/assoc/{}/confirm'.format(self.joeuser.id))
        a = Assoc.objects.create(member=self.joeuser, band=self.band)
        self.assertFalse(a.status==AssocStatusChoices.CONFIRMED)

        # make sure a superuser can confirm an assoc for another user
        request.user = self.super
        helpers.confirm_assoc(request, a.id)
        a = Assoc.objects.get(band=self.band, member=self.joeuser)
        self.assertTrue(a.status==AssocStatusChoices.CONFIRMED)
        a.status=AssocStatusChoices.CONFIRMED
        a.save()

        # make sure a band admin can create an assoc for another user for their band
        request.user = self.band_admin
        helpers.confirm_assoc(request, a.id)
        a = Assoc.objects.get(band=self.band, member=self.joeuser)
        self.assertTrue(a.status==AssocStatusChoices.CONFIRMED)
        a.status = AssocStatusChoices.NOT_CONFIRMED
        a.save()

        # make sure nobody else can
        request.user = self.janeuser
        with self.assertRaises(PermissionError):
            helpers.confirm_assoc(request, ak=a.id)

    def test_deleting_section(self):

        # be sure we're a member of the default section
        assoc = Assoc.objects.get(band=self.band, member=self.band_admin)
        self.assertTrue(assoc.default_section.is_default)

        # make a new section
        new_section = Section.objects.create(band=self.band, name="foohorn")
        assoc.default_section=new_section
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
        self.assertEqual(assoc.default_section,self.band.sections.get(is_default=True))

class BandTests(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        """ make sure we get rid of anything we made """
        Member.objects.all().delete()
        Band.objects.all().delete()
        Assoc.objects.all().delete()

    def test_band_member_queries(self):
        band = Band.objects.create(name='test band')
        self.assertEqual(band.all_assocs.count(), 0)
        self.assertEqual(band.confirmed_assocs.count(), 0)
        joeuser = Member.objects.create_user(email='g@h.i')
        a=Assoc.objects.create(member=joeuser, band=band, is_admin=True)
        self.assertEqual(band.all_assocs.count(), 1)
        self.assertEqual(band.confirmed_assocs.count(), 0)
        a.status = AssocStatusChoices.CONFIRMED
        a.save()
        self.assertEqual(band.confirmed_assocs.count(), 1)
        joeuser.status = MemberStatusChoices.DORMANT
        joeuser.save()
        self.assertEqual(band.all_assocs.count(), 0)
        self.assertEqual(band.confirmed_assocs.count(), 0)
