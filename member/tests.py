from django.test import TestCase, RequestFactory
from .models import Member, MemberPreferences
from band.models import Band, Assoc
from .views import AssocsView, OtherBandsView

class MemberTest(TestCase):
    def setUp(self):
        m=Member.objects.create_user('a@b.com', password='abc')
        b=Band.objects.create(name='test band')
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
        self.assertEqual(len(m.assocs.all()),1)
        b = m.assocs.first().band
        self.assertEqual(b.name, 'test band')

    def test_memberassocsview(self):
        m = Member.objects.first()
        request = RequestFactory().get('/member/{}/assocs/'.format(m.id))
        view = AssocsView()
        view.setup(request, pk='{}'.format(m.id))

        context = view.get_context_data()
        self.assertIn('assocs', context)
        self.assertEqual(len(context['assocs']),1)
        self.assertEqual(context['assocs'][0].band.name, 'test band')

    def test_member_otherbandsview(self):
        m = Member.objects.first()
        request = RequestFactory().get('/member/{}/otherbands/'.format(m.id))
        view = OtherBandsView()
        view.setup(request, pk='{}'.format(m.id))

        context = view.get_context_data()
        self.assertIn('bands', context)
        self.assertEqual(len(context['bands']),1)
        self.assertEqual(context['bands'][0].name, 'another band')


