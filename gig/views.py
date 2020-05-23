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
import datetime
from django.shortcuts import get_object_or_404, render
from django.views import generic
from django.urls import reverse
from django.utils import timezone
from django import forms
from django.http import Http404
from .models import Gig, Plan
from .forms import GigForm
from .util import PlanStatusChoices
from band.models import Band
from gig.helpers import notify_new_gig


class DetailView(generic.DetailView):
    model = Gig

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # todo or band members, admins etc.
        context['user_can_edit'] = self.request.user.is_superuser
        # todo or band members, admins etc.
        context['user_can_create'] = self.request.user.is_superuser
        context['timezone'] = self.object.band.timezone

        if self.object.address:
            if self.object.address.startswith('http'):
                context['address_string'] = self.object.address
            else:
                context['address_string'] = f'http://maps.google.com?q={self.object.address}'

        timezone.activate(self.object.band.timezone)

        return context


class CreateView(generic.CreateView):
    model = Gig
    form_class = GigForm

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_success_url(self):
        return reverse('gig-detail', kwargs={'pk': self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_new'] = True
        context['band'] = self.get_band_from_kwargs(**kwargs)
        context['timezone'] = context['band'].timezone
        return context

    def get_band_from_kwargs(self, **kwargs):
         return Band.objects.get(id=self.kwargs['bk'])

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(CreateView, self).get_form_kwargs(*args, **kwargs)
        kwargs['band'] = self.get_band_from_kwargs(**kwargs)
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        band = Band.objects.get(id=self.kwargs['bk'])
        if not has_edit_permission(self.request.user, band):
            raise PermissionError("Trying to create a gig without permission: {}".format(
                self.request.user.email))

        # there's a new gig; link it to the band
        form.instance.band = band

        result = super().form_valid(form)

        # call the super before sending notifications, so the object is saved
        if form.cleaned_data['send_update']:
            notify_new_gig(form.instance, created=True)

        return result


class UpdateView(generic.UpdateView):
    model = Gig
    form_class = GigForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['timezone'] = self.object.band.timezone
        return context

    def get_success_url(self):
        return reverse('gig-detail', kwargs={'pk': self.object.id})

    def clean_date(self):
        pass

    def form_valid(self, form):
        if not has_edit_permission(self.request.user, self.object.band):
            raise PermissionError("Trying to update a gig without permission: {}".format(
                self.request.user.email))

        result = super(UpdateView, self).form_valid(form)

        # call the super before sending notifications, so the object is saved
        if form.cleaned_data['send_update']:
            notify_new_gig(form.instance, created=False)

        return result

class DuplicateView(CreateView):
  
    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        gig_orig = Gig.objects.get(id=self.kwargs['pk'])
        # we didn't originally get a band in the request, we got a gig pk - so get the band from that
        # and stash it among the args from the request
        self.kwargs['bk'] = gig_orig.band.id

        # populate the initial data from the original gig
        kwargs['initial'] = forms.models.model_to_dict(gig_orig, 
                                                        exclude=['calldate', 'setdate', 'enddate'])
        # ...but replace the title with a 'copy of'
        kwargs['initial']['title'] = f'Copy of {kwargs["initial"]["title"]}'
        return kwargs

    def get_band_from_kwargs(self, **kwargs):
        # didn't have the band from the request args, so pull it from the gig
        return get_object_or_404(Gig, id=self.kwargs['pk']).band


def has_edit_permission(user, band):
        return user.is_superuser or band.anyone_can_create_gigs or band.is_admin(user)

def answer(request, pk, val):
    plan = get_object_or_404(Plan, pk=pk)
    plan.status = val
    if val == PlanStatusChoices.DONT_KNOW:
        now = datetime.datetime.now(tz=timezone.get_current_timezone())
        if (future_days := (plan.gig.date - now).days) > 8:
            plan.snooze_until = now + datetime.timedelta(days=7)
        elif future_days > 2:
            plan.snooze_until = plan.gig.date - datetime.timedelta(days=2)
    plan.save()
    return render(request, 'gig/answer.html', {'gig_id': plan.gig.id})
