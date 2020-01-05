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
from .models import Band, Assoc
from member.models import Member
from band import helpers

class MemberTest(TestCase):
    def setUp(self):
        self.super = Member.objects.create_user(email='a@b.c', is_superuser=True)
        self.band_admin = Member.objects.create_user(email='d@e.f')
        self.joeuser = Member.objects.create_user(email='g@h.i')
        self.janeuser = Member.objects.create_user(email='j@k.l')
        self.band = Band.objects.create(name='test band')
        Assoc.objects.create(member=self.band_admin, band=self.band, is_band_admin=True)

    def tearDown(self):
        """ make sure we get rid of anything we made """
        Member.objects.all().delete()
        Band.objects.all().delete()
        Assoc.objects.all().delete()


    def test_addband(self):

        request = RequestFactory().get('/band/assoc/create/{}/{}'.format(self.band.id, self.joeuser.id))

        # make sure a user can create their own assoc
        request.user = self.joeuser
        helpers.create_assoc(request, bk=self.band.id, mk=self.joeuser.id)
        a = Assoc.objects.get(band=self.band, member=self.joeuser)
        a.delete()

        # make sure a superuser can create an assoc for another user
        request.user = self.super
        helpers.create_assoc(request, bk=self.band.id, mk=self.joeuser.id)
        a = Assoc.objects.get(band=self.band, member=self.joeuser)
        a.delete()

        # make sure a band admin can create an assoc for another user for their band
        request.user = self.band_admin
        
        self.assertEqual(Assoc.objects.count(), 1)
        a = Assoc.objects.get(band=self.band, member=self.band_admin)
        self.assertEqual(a.is_band_admin, True)

        helpers.create_assoc(request, bk=self.band.id, mk=self.joeuser.id)
        a = Assoc.objects.get(band=self.band, member=self.joeuser)
        a.delete()

        # make sure nobody else can
        request.user = self.janeuser
        with self.assertRaises(PermissionError):
            helpers.create_assoc(request, bk=self.band.id, mk=self.joeuser.id)

        # make sure we can't have two assocs to the same band
        request.user = self.band_admin
        helpers.create_assoc(request, bk=self.band.id, mk=self.joeuser.id)
        helpers.create_assoc(request, bk=self.band.id, mk=self.joeuser.id)
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
        self.assertFalse(a.is_confirmed)

        # make sure a superuser can confirm an assoc for another user
        request.user = self.super
        helpers.confirm_assoc(request, a.id)
        a = Assoc.objects.get(band=self.band, member=self.joeuser)
        self.assertTrue(a.is_confirmed)
        a.is_confirmed=False
        a.save()

        # make sure a band admin can create an assoc for another user for their band
        request.user = self.band_admin
        helpers.confirm_assoc(request, a.id)
        a = Assoc.objects.get(band=self.band, member=self.joeuser)
        self.assertTrue(a.is_confirmed)
        a.is_confirmed=False
        a.save()

        # make sure nobody else can
        request.user = self.janeuser
        with self.assertRaises(PermissionError):
            helpers.confirm_assoc(request, ak=a.id)

