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
    fields = ['name', 'hometown']

    def get_context_data(self, **kwargs):
        the_band = self.object
        the_user = self.request.user

        context = super().get_context_data(**kwargs)

        assocs = Assoc.objects.filter(band=the_band, member=the_user)
        if len(assocs) != 1:
            context['the_user_is_associated'] = False
        else:
            context['the_user_is_associated'] = True
            a = assocs[0]
            context['the_user_is_band_admin'] = a.is_band_admin
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
        context['member_assocs'] = Assoc.objects.filter(band__id=self.kwargs['pk']).filter(is_confirmed=True)
        return context



class SectionMembersView(LoginRequiredMixin, TemplateView):
    template_name='band/band_section_members.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        b = Band.objects.filter(id=self.kwargs['pk'])
        if len(b) != 1:
            raise ValueError('getting section info on a band that does not exist')
        b = b[0]

        if self.kwargs['sk']:
            s = Section.objects.filter(id=self.kwargs['sk'])
            if len(s) != 1:
                raise ValueError('getting info on a section that does not exist')
            s = s[0]
        else:
            s = None

        context['has_sections'] = True if len(b.sections.all()) > 0 else False
        context['the_section'] = s
        context['the_assocs'] = b.assocs.filter(default_section = s).all()
        print('\n\n{0}\n\n'.format(context['the_assocs']))
        return context

