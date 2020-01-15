from django.http import HttpResponse
from .models import Band, Assoc, Section
from django.views import generic
from django.views.generic.edit import UpdateView as BaseUpdateView
from django.views.generic.base import TemplateView
from django.urls import reverse
from .forms import BandForm
from django.contrib.auth.mixins import LoginRequiredMixin

def index(request):
    return HttpResponse("Hello, world. You're at the band index.")

class DetailView(generic.DetailView):
    model = Band
    # fields = ['name', 'hometown']

    def get_context_data(self, **kwargs):
        the_band = self.object
        the_user = self.request.user

        context = super().get_context_data(**kwargs)

        assoc = Assoc.objects.filter(band=the_band, member=the_user).first()
        if assoc is None:
            context['the_user_is_associated'] = False
        else:
            context['the_user_is_associated'] = True
            context['the_user_is_band_admin'] = assoc.is_admin

            context['the_pending_members'] = Assoc.objects.filter(band=the_band, status=Assoc.StatusChoices.PENDING)
        return context

    def get_success_url(self):
        return reverse('member-detail', kwargs={'pk': self.object.id})


class UpdateView(LoginRequiredMixin, BaseUpdateView):
    model = Band
    form_class = BandForm
    def get_success_url(self):
        return reverse('band-detail', kwargs={'pk': self.object.id})


class AllMembersView(LoginRequiredMixin, TemplateView):
    template_name='band/band_all_members.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['member_assocs'] = Assoc.band_assocs.confirmed_assocs(self.kwargs['pk'])
        return context

class SectionMembersView(LoginRequiredMixin, TemplateView):
    template_name='band/band_section_members.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        b = Band.objects.filter(id=self.kwargs['pk'])
        # prefetching seems to his the database more
        # b = Band.objects.prefetch_related('assocs').filter(id=self.kwargs['pk'])
        if len(b) != 1:
            raise ValueError('getting section info on a band that does not exist')
        b = b[0]

        # make sure I'm in the band or am superuser
        u = self.request.user
        if  u.is_superuser is False and len(b.assocs.confirmed.filter(member=u, member__is_active=True))!=1:
            raise ValueError('user {0} accessing section members for non-member band'.format(u.email))

        if self.kwargs['sk']:
            s = Section.objects.filter(id=self.kwargs['sk'])
            if len(s) != 1:
                raise ValueError('getting info on a section that does not exist')

            s = s[0]

            if s.band != b:
                raise ValueError('accessing a section by wrong band')
        else:
            s = None

        context['has_sections'] = True if len(b.sections.all()) > 0 else False
        context['the_section'] = s
        context['the_assocs'] = b.assocs.filter(status=Assoc.StatusChoices.CONFIRMED, default_section=s, member__is_active=True).all()
        return context

