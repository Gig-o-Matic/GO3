from django.test import TestCase, RequestFactory
from .models import Band, Assoc
from member.models import Member
from band import helpers

class MemberTest(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        """ make sure we get rid of anything we made """
        Member.objects.all().delete()
        Band.objects.all().delete()
        Assoc.objects.all().delete()


    def test_addband(self):
        m1 = Member.objects.create_user(email="a@b.c")
        m2 = Member.objects.create_user(email="d@e.f")
        b = Band.objects.create(name="test band")

        request = RequestFactory().get('/band/assoc/create/{}/{}'.format(b.id, m1.id))

        # make sure only a user can create their own assoc
        request.user = m2
        with self.assertRaises(PermissionError):
            helpers.create_assoc(request, bk=b.id, mk=m1.id)

        request.user = m1
        helpers.create_assoc(request, bk=b.id, mk=m1.id)

        # make sure we have an assoc
        self.assertEqual(len(Assoc.objects.all()), 1)

        # make sure we can't have two assocs to the same band
        helpers.create_assoc(request, bk=b.id, mk=m1.id)
        self.assertEqual(len(Assoc.objects.all()), 1)



    def test_leaveband(self):
        m = Member.objects.create_user(email="a@b.c")
        m2 = Member.objects.create_user(email="d@e.f")
        b = Band.objects.create(name="test band")
        a = Assoc.objects.create(band=b, member=m)

        # make sure we have an assoc
        self.assertEqual(len(Assoc.objects.all()), 1)

        request = RequestFactory().get('/band/assoc/{}/delete'.format(a.id))

        # make sure only a user can delete their own assoc
        request.user = Member.objects.last()
        with self.assertRaises(PermissionError):
            helpers.delete_assoc(request, ak=a.id)

        request.user = Member.objects.first()
        helpers.delete_assoc(request, ak=a.id)

        # make sure we have no assoc
        self.assertEqual(len(Assoc.objects.all()), 0)

