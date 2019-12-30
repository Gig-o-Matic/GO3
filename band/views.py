from django.http import HttpResponse
from .models import Band, Assoc
from django.views import generic
from django.views.generic.edit import UpdateView as BaseUpdateView
from django.urls import reverse
from .forms import BandForm


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

class UpdateView(BaseUpdateView):
    model = Band
    # fields = ['name', 'shortname', 'hometown', 'description', 'member_links', 'website',
    #           'new_member_message', 'thumbnail_img', 'images', 'timezone',
    #           'anyone_can_create_gigs', 'anyone_can_manage_gigs', 'share_gigs',
    #           'send_updates_by_default', 'rss_feed', 'simple_planning', 'plan_feedback']
    form_class = BandForm
    def get_success_url(self):
        return reverse('band-detail', kwargs={'pk': self.object.id})
