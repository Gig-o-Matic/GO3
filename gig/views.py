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
from pytz import utc
from django.shortcuts import get_object_or_404, render
from django.views import generic
from django.views.generic.base import TemplateView
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q
from django.db.models.functions import Lower
from django import forms
from django.http import HttpResponseForbidden
from .models import Gig, Plan, GigComment
from .forms import GigForm
from .util import PlanStatusChoices
from .helpers import create_gig_series
from band.models import Band, Assoc
from gig.helpers import notify_new_gig
from member.helpers import has_band_admin, has_manage_gig_permission, has_create_gig_permission, has_comment_permission
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from validators import url as url_validate

class DetailView(LoginRequiredMixin, UserPassesTestMixin, generic.DetailView):
    model = Gig

    def test_func(self):
        # can only see the gig if you're logged in and in the band
        gig = get_object_or_404(Gig, id=self.kwargs['pk'])
        return gig.band.has_member(self.request.user) or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['the_user_is_band_admin'] = has_band_admin(
            self.request.user, self.object.band)
        context['user_has_manage_gig_permission'] = has_manage_gig_permission(
            self.request.user, self.object.band) or self.object.creator == self.request.user
        context['user_has_create_gig_permission'] = has_create_gig_permission(
            self.request.user, self.object.band)

        if self.object.enddate:
            context['multi_day_gig'] = self.object.is_full_day
        else:
            context['multi_day_gig'] = False

        if not self.object.is_full_day:
            context['call_time'] = self.object.date if self.object.has_call_time else None
            context['set_time'] = self.object.setdate if self.object.has_set_time else None
            context['end_time'] = self.object.enddate if self.object.has_end_time else None

        context['plan_list'] = [x.value for x in PlanStatusChoices]

        # filter the plans so we only see plans for regular users, or occasionals who have registered,
        # or the current user
        # VERY IMPORTANT! The order of these results MUST be group by section, or the template breaks.
        # See https://github.com/Gig-o-Matic/GO3/pull/251
        context['gig_ordered_member_plans'] = self.object.member_plans.filter(
            Q(assoc__is_occasional=False) | Q(assoc__member=self.request.user) | ~Q(status=PlanStatusChoices.NO_PLAN)
            ).order_by('section',Lower('assoc__member__display_name'))

        if self.object.address:
            if url_validate(self.object.address):
                context['address_string'] = self.object.address
            elif url_validate(f'http://{self.object.address}'):
                # if there's no scheme, see if it works with http
                context['address_string'] = f'http://{self.object.address}'
            else:
                context['address_string'] = f'http://maps.google.com?q={self.object.address}'

        return context


class CreateView(LoginRequiredMixin, UserPassesTestMixin, generic.CreateView):
    model = Gig
    form_class = GigForm

    def test_func(self):
        # can only create the gig if you're logged in and in the band
        band = get_object_or_404(Band, id=self.kwargs['bk'])
        return has_create_gig_permission(self.request.user, band)

    def get_success_url(self):
        return reverse('gig-detail', kwargs={'pk': self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_new'] = True
        context['band'] = self.get_band()
        context['timezone'] = context['band'].timezone
        return context

    def get_band(self):
        """ for a createview where we have a band passed into the view as a key, use it """
        return Band.objects.get(id=self.kwargs['bk'])

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(CreateView, self).get_form_kwargs(*args, **kwargs)

        # we need to do this because there are some form fields that do not exist in the object,
        # so we need all of the initial values from the object so we can get at them
        # from the template.
        if (self.object):
            kwargs['initial'] = forms.models.model_to_dict(self.object)

        kwargs['band'] = self.get_band()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        band = Band.objects.get(id=self.kwargs['bk'])
        if not has_create_gig_permission(self.request.user, band):
            return HttpResponseForbidden()

        # there's a new gig; link it to the band
        form.instance.band = band
        form.instance.creator = self.request.user

        result = super().form_valid(form)

        # call the super before sending notifications, so the object is saved

        if form.cleaned_data['add_series']:
            the_dates = create_gig_series(form.instance, form.cleaned_data['total_gigs'], form.cleaned_data['repeat'])
            if form.cleaned_data['email_changes']:
                notify_new_gig(form.instance, created=True, dates=the_dates)
        else:
            if form.cleaned_data['email_changes']:
                notify_new_gig(form.instance, created=True)

        return result




class UpdateView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = Gig
    form_class = GigForm

    def test_func(self):
        # can only edit the gig if you're logged in and in the band
        gig = get_object_or_404(Gig, id=self.kwargs['pk'])
        return has_manage_gig_permission(self.request.user, gig.band) or (gig.creator==self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['timezone'] = self.object.band.timezone

        # Copy the date & time values from the form into context so the templates can reference them
        context['call_date'] = self.object.date
        context['set_time'] = self.object.setdate
        context['end_date'] = self.object.enddate

        return context

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)

        # we need to do this because there are some form fields that do not exist in the object,
        # so we need all of the initial values from the object so we can get at them
        # from the template.
        return kwargs

    def get_success_url(self):
        return reverse('gig-detail', kwargs={'pk': self.object.id})


    def form_valid(self, form):
        if not has_manage_gig_permission(self.request.user, self.object.band):
            return HttpResponseForbidden()

        result = super(UpdateView, self).form_valid(form)

        # call the super before sending notifications, so the object is saved
        if form.cleaned_data['email_changes']:
            notify_new_gig(form.instance, created=False)

        return result


class DuplicateView(CreateView):

    original_gig = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.original_gig = get_object_or_404(Gig, id=self.kwargs['pk'])

    def test_func(self):
        if not self.request.user.is_authenticated:
            return self.handle_no_permission()
        gig = get_object_or_404(Gig, id=self.kwargs['pk'])
        return has_create_gig_permission(self.request.user, gig.band)

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        # we didn't originally get a band in the request, we got a gig pk - so get the band from that
        # and stash it among the args from the request
        self.kwargs['bk'] = self.original_gig.band.id


        # populate the initial data from the original gig
        kwargs['initial'] = forms.models.model_to_dict(self.original_gig)
        # ...but replace the title with a 'copy of'
        kwargs['initial']['title'] = f'Copy of {kwargs["initial"]["title"]}'
        return kwargs

    def get_band(self):
        """ for a duplicate where we don't have the band passed in but we have the """
        """ original gig, return the band from it """
        return self.original_gig.band


class CommentsView(UserPassesTestMixin, TemplateView):
    template_name = 'gig/gig_comments.html'

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return self.handle_no_permission()
        gig = get_object_or_404(Gig, id=self.kwargs['pk'])
        return gig.band.has_member(user) or user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gig = Gig.objects.get(id=self.kwargs['pk'])
        context['gig'] = gig
        try:
            context['comments'] = GigComment.objects.filter(
                gig__id=self.kwargs['pk']).order_by('created_date')
        except GigComment.DoesNotExist:
            context['comments'] = None
        return context

    def get(self, request, *args, **kwargs):
        if not has_comment_permission(self.request.user, get_object_or_404(Gig, id=kwargs['pk'])):
            return HttpResponseForbidden()
        return super().get(request, **kwargs)

    def post(self, request, **kwargs):
        if not has_comment_permission(self.request.user, get_object_or_404(Gig, id=kwargs['pk'])):
            return HttpResponseForbidden()

        text = request.POST.get('commenttext', '').strip()
        if text:
            GigComment.objects.create(
                text=text, member=request.user, gig=Gig.objects.get(id=kwargs['pk']))
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)


class PrintPlansView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'gig/gig_print_planlist.html'

    def test_func(self):
        # can only see the gig if you're logged in and in the band
        gig = get_object_or_404(Gig, id=self.kwargs['pk'])
        return gig.band.has_member(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gig = Gig.objects.get(id=self.kwargs['pk'])
        context['gig'] = gig
        context['gig_ordered_member_plans'] = gig.member_plans.order_by('section_id', Lower('assoc__member__display_name'))
        context['plan_list'] = PlanStatusChoices.labels
        context['all'] = kwargs.get('all', True)
        return context


class PrintSetlistView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'gig/gig_print_setlist.html'

    def test_func(self):
        # can only see the gig if you're logged in and in the band
        gig = get_object_or_404(Gig, id=self.kwargs['pk'])
        return gig.band.has_member(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gig = Gig.objects.get(id=self.kwargs['pk'])
        context['gig'] = gig
        return context


def answer(request, pk, val):
    """ update the answer via URL. If we have a snooze reminder set it will be unset in the plan save signal """
    plan = get_object_or_404(Plan, pk=pk)
    plan.status = val
    if val == PlanStatusChoices.DONT_KNOW:
        now = datetime.datetime.now()
        if (future_days := (plan.gig.date.date() - now.date()).days) > 8:
            plan.snooze_until = now.replace(tzinfo=utc) + datetime.timedelta(days=7)
        elif future_days > 2:
            plan.snooze_until = plan.gig.date.replace(tzinfo=utc) - datetime.timedelta(days=2)
    plan.save()
    return render(request, 'gig/answer.html', {'gig_id': plan.gig.id})
