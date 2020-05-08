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

from django.http import HttpResponse, JsonResponse
from .forms import MemberCreateForm, InviteForm
from .models import Member, MemberPreferences, Invite
from band.models import Band, Assoc, AssocStatusChoices
from lib.translation import join_trans
from django.views import generic
from django.views.decorators.http import require_POST
from django.views.generic.edit import UpdateView as BaseUpdateView, CreateView, FormView
from django.urls import reverse
from django.views.generic.base import TemplateView
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from go3.colors import the_colors
from django.utils import translation
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.core.validators import validate_email
from django.core.exceptions import PermissionDenied, ValidationError

def index(request):
    return HttpResponse("Hello, world. You're at the member index.")

class DetailView(LoginRequiredMixin, generic.DetailView):
    model = Member
    template_name = 'member/member_detail.html'

    def get_context_data(self, **kwargs):

        the_member = self.object
        the_user = self.request.user

        ok_to_show = False
        same_band = False
        if the_member.id == the_user.id:
            is_me = True
            ok_to_show = True
        else:
            is_me = False

        # # find the bands this member is associated with
        the_member_bands = [a.band for a in the_member.assocs.all()]

        if is_me == False:
            # are we at least in the same band, or superuser?
            if the_user.is_superuser:
                ok_to_show = True
            # TODO What is all this?
            # the_other_band_keys = assoc.get_band_keys_of_member_key(the_member_key=the_user.key, confirmed_only=True)
            # for b in the_other_band_keys:
            #     if b in the_band_keys:
            #         ok_to_show = True
            #         same_band = True
            #         break
            # if ok_to_show == False:
            #     # check to see if we're sharing our profile - if not, bail!
            #     if (the_member.preferences and the_member.preferences.share_profile == False) and the_user.is_superuser == False:
            #         return self.redirect('/')

        # email_change = self.request.get('emailAddressChanged',False)
        # if email_change:
        #     email_change_msg='You have selected a new email address - check your inbox to verify!'
        # else:
        #     email_change_msg = None

        # if I'm not sharing my email, don't share my email
        show_email = False
        if the_member.id == the_user.id or the_user.is_superuser:
            show_email = True
        elif the_member.preferences.share_profile and the_member.preferences.share_email:
            show_email = True

        show_phone = False
        if the_member == the_user.id or the_user.is_superuser:
            show_phone = True
        else:
            # are we in the same band? If so, always show email and phone
            if same_band:
                show_phone = True
                show_email = True

        context = super().get_context_data(**kwargs)
        context['the_member_bands'] = the_member_bands
        context['show_email'] = show_email
        context['show_phone'] = show_phone
        context['member_is_me'] = the_user.id == the_member.id
        if is_me or the_user.is_superuser:
            context['invites'] = Invite.objects.filter(email=the_user.email, band__isnull=False)
        else:
            context['invites'] = None

        return context


class UpdateView(BaseUpdateView):
    model = Member
    fields = ['email','username','nickname','phone','statement','images']

    def get_success_url(self):
        return reverse('member-detail', kwargs={'pk': self.object.id})

class PreferencesUpdateView(BaseUpdateView):
    model = MemberPreferences
    fields = ['hide_canceled_gigs','language','share_profile','share_email','calendar_show_only_confirmed',
              'calendar_show_only_committed']

    def get_success_url(self):
        return reverse('member-detail', kwargs={'pk': self.object.id})

    def form_valid(self, form):
        translation.activate(self.object.language)
        response = super().form_valid(form)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, self.object.language )
        return response


class AssocsView(LoginRequiredMixin, TemplateView):
    template_name='member/member_assocs.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assocs'] = Assoc.objects.select_related('band').filter(member__id = self.kwargs['pk'])
        context['the_colors'] = the_colors
        return context


class OtherBandsView(LoginRequiredMixin, TemplateView):
    template_name='member/member_band_popup.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bands'] = Band.objects.exclude(assocs__in=Assoc.objects.filter(member__id=self.kwargs['pk']))
        return context


class InviteView(LoginRequiredMixin, FormView):
    template_name = 'member/band_invite.html'
    form_class = InviteForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        band = get_object_or_404(Band, pk=self.kwargs['bk'])
        context['band'] = band
        return context

    def form_valid(self, form):
        band = get_object_or_404(Band, pk=self.kwargs['bk'])
        emails = form.cleaned_data['emails'].replace(',', ' ').split()

        user_is_band_admin = Assoc.objects.filter(
            member=self.request.user, band=band, is_admin=True).count() == 1

        if not (user_is_band_admin or self.request.user.is_superuser):
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
                Invite.objects.create(band=band, email=email, language=self.request.user.preferences.language)
                invited.append(email)

        self.return_to_form = False
        if invalid:
            messages.error(self.request,
                           format_lazy(_('Invalid email addresses: {e}'),
                                       e=join_trans(_(', '), invalid)))
            self.return_to_form = True
        if invited:
            messages.success(self.request,
                             format_lazy(_('Invitations sent to {e}'),
                                         e=join_trans(_(', '), invited)))
        if in_band:
            messages.info(self.request,
                          format_lazy(_('These users are already in the band: {e}'),
                                      e=join_trans(_(', '), in_band)))

        return super().form_valid(form)

    def get_success_url(self):
        if self.return_to_form:
            return reverse('member-invite', args=[self.kwargs['bk']])
        return reverse('band-detail', args=[self.kwargs['bk']])


def accept_invite(request, pk):
    invite = get_object_or_404(Invite, pk=pk)

    if not (request.user.is_authenticated or settings.LANGUAGE_COOKIE_NAME in request.COOKIES):
        # We need the language active before we try to render anything.
        translation.activate(invite.language)
        def set_language(response):
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, invite.language)
            return response
    else:
        def set_language(response):
            return response

    if request.user.is_authenticated and request.GET.get('claim') == 'true':
        member = request.user
    else:
        member = Member.objects.filter(email=invite.email).first()

    if (member and                             # Won't need to create a Member
        (not request.user.is_authenticated or  # They're probably just not logged in
         request.user == member)):             # They are logged in
        if invite.band and Assoc.objects.filter(band=invite.band, member=member).count() == 0:
            Assoc.objects.create(band=invite.band, member=member,
                                 status=AssocStatusChoices.CONFIRMED)
            if request.user.is_authenticated:
                # We'll be redirecting them to their profile page, and we want to display:
                messages.success(request,
                                 format_lazy(_('You are now a member of {band}.'),
                                             band=invite.band.name))
        invite.delete()
        if request.user.is_authenticated:
            return redirect('member-detail', pk=member.id)
        return set_language(
                   render(request, 'member/accepted.html',
                          {'band_name': invite.band.name if invite.band else None,
                          'member_id': member.id}))

    if request.user.is_authenticated:  # The user is signed in, but as a different user
        return render(request, 'member/claim_invite.html', {'invite': invite, 'member': member})

    # New user
    return set_language(redirect('member-create', pk=invite.id))


class MemberCreateView(CreateView):
    template_name = 'member/create.html'
    form_class = MemberCreateForm
    model = Member

    def get_form_kwargs(self):
        self.invite = get_object_or_404(Invite, pk=self.kwargs['pk'])
        translation.activate(self.invite.language)
        kwargs = super().get_form_kwargs()
        kwargs['invite'] = self.invite
        return kwargs

    def get_context_data(self, **kw):
        context = super().get_context_data(**kw)
        context['email'] = self.invite.email
        context['band_name'] = self.invite.band.name if self.invite.band else None
        return context

    def form_valid(self, form):
        retval = super().form_valid(form)
        member = authenticate(username=self.invite.email, password=form.cleaned_data['password1'])
        member.preferences.language = self.invite.language
        #member.preferences.save()  # Why isn't this necessary?
        login(self.request, member)
        return retval

    def get_success_url(self):
        return reverse('member-invite-accept', kwargs={'pk': str(self.invite.id)})


@login_required
def delete_invite(request, pk):
    invite = get_object_or_404(Invite, pk=pk)
    user_is_band_admin = Assoc.objects.filter(
        member=request.user, band=invite.band, is_admin=True).count() == 1
    user_is_invitee = (request.user.email == invite.email)
    if not (user_is_band_admin or user_is_invitee or request.user.is_superuser):
        raise PermissionDenied

    invite.delete()
    if user_is_invitee:
        messages.info(request,
                      format_lazy(_('Your invitation to join {band} has been deleted.'),
                                  band=invite.band.name if invite.band else 'Gig-O-Matic'))
        return redirect('member-detail', pk=request.user.id)
    return redirect('band-detail', pk=invite.band.id)


@require_POST
def signup(request):
    email = request.POST.get('email')
    if Member.objects.filter(email=email).count() > 0:
        return JsonResponse({'status': 'failure', 'error': 'member exists'})
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'status': 'failure', 'error': 'invalid email'})
    Invite.objects.create(band=None, email=email)
    return JsonResponse({'status': 'success'})
