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

from django.http import HttpResponse, JsonResponse, HttpResponseNotFound
from .forms import MemberCreateForm, InviteForm, SignupForm, MemberChangeForm
from .models import Member, MemberPreferences, Invite, EmailConfirmation
from band.models import Band, Assoc, AssocStatusChoices
from member.util import MemberStatusChoices
from lib.translation import join_trans
from django.views import generic
from django.views.decorators.http import require_POST
from django.views.generic.edit import UpdateView as BaseUpdateView, CreateView, FormView
from django.urls import reverse
from django.views.generic.base import TemplateView
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
    AccessMixin,
)
from django.contrib.auth.views import PasswordChangeDoneView, PasswordResetView
from django.contrib import messages
from go3.colors import the_colors
from django.utils import translation
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.core.validators import validate_email
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from lib.captcha import verify_captcha, get_captcha_site_key


def verify_requester_is_user(request, user):
    if not (request.user.id == user.id or request.user.is_superuser):
        raise PermissionDenied


def verify_requestor_is_in_user_band(request, user):
    """
    make sure that whoever is requesting to see a member's details
    is in the band with that member
    """
    if request.user.id == user.id or request.user.is_superuser:
        return True

    rbands = [a.band for a in request.user.confirmed_assocs]
    ubands = [a.band for a in user.confirmed_assocs]
    if len(set(rbands) & set(ubands)) == 0:
        raise PermissionDenied
    return True


class DetailView(LoginRequiredMixin, UserPassesTestMixin, generic.DetailView):
    model = Member
    template_name = "member/member_detail.html"

    def test_func(self):
        # can see the member if we're in the same band or are superuser
        return self.request.user.is_superuser or verify_requestor_is_in_user_band(
            self.request, self.get_object()
        )

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except AttributeError:
            return self.request.user

    def get_context_data(self, **kwargs):

        the_member = self.object
        the_user = self.request.user

        verify_requestor_is_in_user_band(self.request, the_member)

        if the_member.id == the_user.id:
            is_me = True
            # ok_to_show = True
        else:
            is_me = False

        # # find the bands this member is associated with
        the_member_bands = [a.band for a in the_member.assocs.all()]

        if the_member.pending_email.count() > 0:
            email_change_msg = _(
                "You have selected a new email address - check your inbox to verify!"
            )
        else:
            email_change_msg = None

        # if I'm not sharing my email, don't share my email
        show_email = False
        if the_member.id == the_user.id or the_user.is_superuser:
            show_email = True
        elif (
            the_member.preferences.share_profile and the_member.preferences.share_email
        ):
            show_email = True

        context = super().get_context_data(**kwargs)
        context["the_member_bands"] = the_member_bands
        context["show_email"] = show_email
        context["member_is_me"] = the_user.id == the_member.id
        context["email_change_msg"] = email_change_msg
        if is_me or the_user.is_superuser:
            context["invites"] = Invite.objects.filter(
                email=the_user.email, band__isnull=False
            )
        else:
            context["invites"] = None
        context["member_images"] = the_member.images.split()

        return context

    def render_to_response(self, context):
        if self.object.status == MemberStatusChoices.DELETED:
            # return HttpResponseNotFound()
            raise Http404
        else:
            return super().render_to_response(context)


class UpdateView(LoginRequiredMixin, BaseUpdateView):
    template_name = "member/member_form.html"
    model = Member
    form_class = MemberChangeForm
    # fields = ['email','username','nickname','phone','statement','images']

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        verify_requester_is_user(self.request, self.object)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        verify_requester_is_user(self.request, self.object)
        return super().post(request, *args, **kwargs)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def form_valid(self, form):
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("member-detail", kwargs={"pk": self.object.id})


class PreferencesUpdateView(LoginRequiredMixin, BaseUpdateView):
    model = MemberPreferences
    fields = [
        "hide_canceled_gigs",
        "language",
        "share_profile",
        "share_email",
        "calendar_show_only_confirmed",
        "calendar_show_only_committed",
    ]

    def get_object(self, queryset=None):
        m = Member.objects.get(id=self.kwargs["pk"])
        return m.preferences

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        verify_requester_is_user(self.request, self.object.member)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        verify_requester_is_user(self.request, self.object.member)
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("member-detail", kwargs={"pk": self.object.member.id})

    def form_valid(self, form):
        translation.activate(self.object.language)
        response = super().form_valid(form)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, self.object.language)

        if (
            "calendar_show_only_confirmed" in form.changed_data
            or "calendar_show_only_committed" in form.changed_data
        ):
            self.object.member.cal_feed_dirty = True
            self.object.member.save()

        return response


class AssocsView(LoginRequiredMixin, TemplateView):
    template_name = "member/member_assocs.html"

    def get(self, request, *args, **kwargs):
        object = get_object_or_404(Member, pk=self.kwargs["pk"])
        verify_requester_is_user(self.request, object)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["assocs"] = Assoc.objects.select_related("band").filter(
            member__id=self.kwargs["pk"]
        )
        context["member_id"] = self.kwargs["pk"]
        context["the_colors"] = the_colors
        return context


class OtherBandsView(LoginRequiredMixin, TemplateView):
    template_name = "member/member_band_popup.html"

    def get(self, request, *args, **kwargs):
        object = get_object_or_404(Member, pk=self.kwargs["pk"])
        verify_requester_is_user(self.request, object)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["bands"] = Band.objects.exclude(
            assocs__in=Assoc.objects.filter(member__id=self.kwargs["pk"])
        ).order_by("name")
        context["member_id"] = self.kwargs["pk"]
        return context


class InviteView(LoginRequiredMixin, FormView):
    template_name = "member/band_invite.html"
    form_class = InviteForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        band = get_object_or_404(Band, pk=self.kwargs["bk"])
        context["band"] = band
        return context

    def form_valid(self, form):
        band = get_object_or_404(Band, pk=self.kwargs["bk"])
        emails = form.cleaned_data["emails"].replace(",", " ").split()

        if not band.is_admin(self.request.user):
            raise PermissionDenied

        invited, in_band, invalid = [], [], []
        for email in emails:
            try:
                validate_email(email)
            except ValidationError:
                invalid.append(email)
                continue

            if Assoc.objects.filter(member__email=email, band=band).count() > 0:
                in_band.append(email)
            else:
                Invite.objects.create(
                    band=band,
                    email=email,
                    language=self.request.user.preferences.language,
                )
                invited.append(email)

        self.return_to_form = False
        if invalid:
            messages.error(
                self.request,
                format_lazy(
                    _("Invalid email addresses: {e}"), e=join_trans(_(", "), invalid)
                ),
            )
            self.return_to_form = True
        if invited:
            messages.success(
                self.request,
                format_lazy(
                    _("Invitations sent to {e}"), e=join_trans(_(", "), invited)
                ),
            )
        if in_band:
            messages.info(
                self.request,
                format_lazy(
                    _("These users are already in the band: {e}"),
                    e=join_trans(_(", "), in_band),
                ),
            )

        return super().form_valid(form)

    def get_success_url(self):
        if self.return_to_form:
            return reverse("member-invite", args=[self.kwargs["bk"]])
        return reverse("band-detail", args=[self.kwargs["bk"]])


def accept_invite(request, pk):
    try:
        invite = Invite.objects.get(pk=pk)
    except Invite.DoesNotExist:
        return render(request, "member/invite_expired.html")

    if not (
        request.user.is_authenticated
        or settings.LANGUAGE_COOKIE_NAME in request.COOKIES
    ):
        # We need the language active before we try to render anything.
        translation.activate(invite.language)

        def set_language(response):
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, invite.language)
            return response

    else:

        def set_language(response):
            return response

    if request.user.is_authenticated and request.GET.get("claim") == "true":
        member = request.user
    else:
        member = Member.objects.filter(email=invite.email).first()

    if member and (  # Won't need to create a Member
        not request.user.is_authenticated
        or request.user == member  # They're probably just not logged in
    ):  # They are logged in
        if (
            invite.band
            and Assoc.objects.filter(band=invite.band, member=member).count() == 0
        ):
            Assoc.objects.create(
                band=invite.band, member=member, status=AssocStatusChoices.CONFIRMED
            )
            if request.user.is_authenticated:
                # We'll be redirecting them to their profile page, and we want to display:
                messages.success(
                    request,
                    format_lazy(
                        _("You are now a member of {band}."), band=invite.band.name
                    ),
                )
        invite.delete()
        if request.user.is_authenticated:
            return redirect("member-detail", pk=member.id)
        return set_language(
            render(
                request,
                "member/accepted.html",
                {
                    "band_name": invite.band.name if invite.band else None,
                    "member_id": member.id,
                },
            )
        )

    if request.user.is_authenticated:  # The user is signed in, but as a different user
        return render(
            request, "member/claim_invite.html", {"invite": invite, "member": member}
        )

    # New user
    return set_language(redirect("member-create", pk=invite.id))


class MemberCreateView(CreateView):
    template_name = "member/create.html"
    form_class = MemberCreateForm
    model = Member

    def get_form_kwargs(self):
        self.invite = get_object_or_404(Invite, pk=self.kwargs["pk"])
        translation.activate(self.invite.language)
        kwargs = super().get_form_kwargs()
        kwargs["invite"] = self.invite
        return kwargs

    def get_context_data(self, **kw):
        context = super().get_context_data(**kw)
        context["email"] = self.invite.email
        context["band_name"] = self.invite.band.name if self.invite.band else None
        return context

    def form_valid(self, form):
        retval = super().form_valid(form)
        member = authenticate(
            username=self.invite.email, password=form.cleaned_data["password1"]
        )
        member.preferences.language = self.invite.language
        # member.preferences.save()  # Why isn't this necessary?
        login(self.request, member)
        return retval

    def get_success_url(self):
        return reverse("member-invite-accept", kwargs={"pk": str(self.invite.id)})


@login_required
def delete_invite(request, pk):
    invite = get_object_or_404(Invite, pk=pk)
    user_is_invitee = request.user.email == invite.email
    if not (
        invite.band.is_admin(request.user)
        or user_is_invitee
        or request.user.is_superuser
    ):
        raise PermissionDenied

    invite.delete()
    if user_is_invitee:
        messages.info(
            request,
            format_lazy(
                _("Your invitation to join {band} has been deleted."),
                band=invite.band.name if invite.band else "Gig-O-Matic",
            ),
        )
        return redirect("member-detail", pk=request.user.id)
    return redirect("band-detail", pk=invite.band.id)


class SignupView(FormView):
    template_name = "member/signup.html"
    form_class = SignupForm

    def get_context_data(self, **kw):
        context = super().get_context_data(**kw)
        context["site_key"] = get_captcha_site_key()
        return context

    def form_valid(self, form):
        # first check the captcha
        if not verify_captcha(self.request):
            return redirect("home")

        email = form.cleaned_data["email"]
        if Member.objects.filter(email=email).count() > 0:
            messages.info(
                self.request,
                format_lazy(
                    _(
                        'An account associated with {email} already exists.  You can recover this account via the "Forgot Password?" link below.'
                    ),
                    email=email,
                ),
            )
            return redirect("home")

        Invite.objects.create(band=None, email=email)
        return render(self.request, "member/signup_pending.html", {"email": email})


class CaptchaPasswordResetView(PasswordResetView):
    """override the default so we can check the captcha"""

    def get_context_data(self, **kw):
        context = super().get_context_data(**kw)
        context["site_key"] = get_captcha_site_key()
        return context

    def form_valid(self, form):
        # first check the captcha
        if not verify_captcha(self.request):
            return redirect("home")
        return super().form_valid(form)


class RedirectPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    def get_success_url(self):
        return redirect("member-detail")


def confirm_email(request, pk):

    valid = True
    try:
        conf = EmailConfirmation.objects.get(pk=pk)
    except EmailConfirmation.DoesNotExist:
        valid = False

    if valid:
        if not (
            request.user.is_authenticated
            or settings.LANGUAGE_COOKIE_NAME in request.COOKIES
        ):
            valid = False
        else:
            conf.member.email = conf.new_email
            conf.member.save()
            conf.delete()

    def set_language(response):
        return response

    return set_language(
        render(request, "member/email_change_confirmation.html", {"validlink": valid})
    )
