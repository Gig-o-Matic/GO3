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
from django.views.generic.base import TemplateView
from django.urls import reverse
from django.utils import timezone
from django import forms
from django.http import Http404, HttpResponseForbidden
from .models import Gig, Plan, GigComment
from .forms import GigForm
from .util import PlanStatusChoices
from band.models import Band, Assoc
from gig.helpers import notify_new_gig
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
import urllib.parse
from validators import url as url_validate


def has_comment_permission(user, gig):
    return user and Assoc.objects.filter(member=user, band=gig.band).count() == 1


def has_manage_permission(user, band):
    return user and (
        user.is_superuser or band.anyone_can_manage_gigs or band.is_admin(user)
    )


def has_create_permission(user, band):
    return user and (
        user.is_superuser or band.anyone_can_create_gigs or band.is_admin(user)
    )


class DetailView(LoginRequiredMixin, UserPassesTestMixin, generic.DetailView):
    model = Gig

    def test_func(self):
        # can only see the gig if you're logged in and in the band
        gig = get_object_or_404(Gig, id=self.kwargs["pk"])
        return gig.band.has_member(self.request.user) or self.request.user.is_superuser

    def get_template_names(self):
        if self.object.is_archived:
            self.template_name_suffix = "_detail_archived"

        t = super().get_template_names()
        return t

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_can_edit"] = has_manage_permission(
            self.request.user, self.object.band
        )
        context["user_can_create"] = has_create_permission(
            self.request.user, self.object.band
        )

        context["timezone"] = self.object.band.timezone

        context["plan_list"] = [x.value for x in PlanStatusChoices]

        if self.object.address:
            if url_validate(self.object.address):
                context["address_string"] = self.object.address
            elif url_validate(f"http://{self.object.address}"):
                # if there's no scheme, see if it works with http
                context["address_string"] = f"http://{self.object.address}"
            else:
                context["address_string"] = (
                    f"http://maps.google.com?q={self.object.address}"
                )

        timezone.activate(self.object.band.timezone)

        return context


class CreateView(LoginRequiredMixin, generic.CreateView):
    model = Gig
    form_class = GigForm

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # cribbed from UserPassesTestMixin
    def dispatch(self, request, *args, **kwargs):
        user_test_result = self.test_func()
        if not user_test_result:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        # can only create the gig if you're logged in and in the band
        band = get_object_or_404(Band, id=self.kwargs["bk"])
        return band.has_member(self.request.user) and has_create_permission(
            self.request.user, band
        )

    def get_success_url(self):
        return reverse("gig-detail", kwargs={"pk": self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_new"] = True
        context["band"] = self.get_band_from_kwargs(**kwargs)
        context["timezone"] = context["band"].timezone
        return context

    def get_band_from_kwargs(self, **kwargs):
        return Band.objects.get(id=self.kwargs["bk"])

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super(CreateView, self).get_form_kwargs(*args, **kwargs)
        kwargs["band"] = self.get_band_from_kwargs(**kwargs)
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        band = Band.objects.get(id=self.kwargs["bk"])
        if not has_create_permission(self.request.user, band):
            return HttpResponseForbidden()

        # there's a new gig; link it to the band
        form.instance.band = band

        result = super().form_valid(form)

        # call the super before sending notifications, so the object is saved
        if form.cleaned_data["send_update"]:
            notify_new_gig(form.instance, created=True)

        return result


class UpdateView(LoginRequiredMixin, generic.UpdateView):
    model = Gig
    form_class = GigForm

    # cribbed from UserPassesTestMixin
    def dispatch(self, request, *args, **kwargs):
        user_test_result = self.test_func()
        if not user_test_result:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        # can only edit the gig if you're logged in and in the band
        gig = get_object_or_404(Gig, id=self.kwargs["pk"])
        return gig.band.has_member(self.request.user) and has_manage_permission(
            self.request.user, gig.band
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["timezone"] = self.object.band.timezone
        return context

    def get_success_url(self):
        return reverse("gig-detail", kwargs={"pk": self.object.id})

    def clean_date(self):
        pass

    def form_valid(self, form):

        if not has_manage_permission(self.request.user, self.object.band):
            return HttpResponseForbidden()

        result = super(UpdateView, self).form_valid(form)

        # call the super before sending notifications, so the object is saved
        if form.cleaned_data["send_update"]:
            notify_new_gig(form.instance, created=False)

        return result


class DuplicateView(UserPassesTestMixin, CreateView):

    def test_func(self):
        if not self.request.user.is_authenticated:
            return self.handle_no_permission()
        gig = get_object_or_404(Gig, id=self.kwargs["pk"])
        return gig.band.is_editor(self.request.user)

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        gig_orig = Gig.objects.get(id=self.kwargs["pk"])
        # we didn't originally get a band in the request, we got a gig pk - so get the band from that
        # and stash it among the args from the request
        self.kwargs["bk"] = gig_orig.band.id

        # populate the initial data from the original gig
        kwargs["initial"] = forms.models.model_to_dict(
            gig_orig, exclude=["calldate", "setdate", "enddate"]
        )
        # ...but replace the title with a 'copy of'
        kwargs["initial"]["title"] = f'Copy of {kwargs["initial"]["title"]}'
        return kwargs

    def get_band_from_kwargs(self, **kwargs):
        # didn't have the band from the request args, so pull it from the gig
        return get_object_or_404(Gig, id=self.kwargs["pk"]).band


class CommentsView(UserPassesTestMixin, TemplateView):
    template_name = "gig/gig_comments.html"

    def test_func(self):
        if not self.request.user.is_authenticated:
            return self.handle_no_permission()
        gig = get_object_or_404(Gig, id=self.kwargs["pk"])
        return gig.band.has_member(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gig = Gig.objects.get(id=self.kwargs["pk"])
        context["gig"] = gig
        try:
            context["comments"] = GigComment.objects.filter(
                gig__id=self.kwargs["pk"]
            ).order_by("created_date")
        except GigComment.DoesNotExist:
            context["comments"] = None
        return context

    def get(self, request, *args, **kwargs):
        if not has_comment_permission(
            self.request.user, get_object_or_404(Gig, id=kwargs["pk"])
        ):
            return HttpResponseForbidden()
        return super().get(request, **kwargs)

    def post(self, request, **kwargs):
        if not has_comment_permission(
            self.request.user, get_object_or_404(Gig, id=kwargs["pk"])
        ):
            return HttpResponseForbidden()

        text = request.POST.get("commenttext", "").strip()
        if text:
            GigComment.objects.create(
                text=text, member=request.user, gig=Gig.objects.get(id=kwargs["pk"])
            )
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)


class PrintPlansView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gig/gig_print_planlist.html"

    def test_func(self):
        # can only see the gig if you're logged in and in the band
        gig = get_object_or_404(Gig, id=self.kwargs["pk"])
        return gig.band.has_member(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gig = Gig.objects.get(id=self.kwargs["pk"])
        context["gig"] = gig
        context["plan_list"] = PlanStatusChoices.labels
        context["all"] = kwargs.get("all", True)
        return context


class PrintSetlistView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "gig/gig_print_setlist.html"

    def test_func(self):
        # can only see the gig if you're logged in and in the band
        gig = get_object_or_404(Gig, id=self.kwargs["pk"])
        return gig.band.has_member(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        gig = Gig.objects.get(id=self.kwargs["pk"])
        context["gig"] = gig
        return context


def answer(request, pk, val):
    """update the answer via URL. If we have a snooze reminder set it will be unset in the plan save signal"""
    plan = get_object_or_404(Plan, pk=pk)
    plan.status = val
    if val == PlanStatusChoices.DONT_KNOW:
        now = datetime.datetime.now(tz=timezone.get_current_timezone())
        if (future_days := (plan.gig.date - now).days) > 8:
            plan.snooze_until = now + datetime.timedelta(days=7)
        elif future_days > 2:
            plan.snooze_until = plan.gig.date - datetime.timedelta(days=2)
    plan.save()
    return render(request, "gig/answer.html", {"gig_id": plan.gig.id})
