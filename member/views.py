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

from django.http import HttpResponse
from .models import Member, MemberPreferences
from band.models import Band, Assoc
from django.views import generic
from django.views.generic.edit import UpdateView as BaseUpdateView
from django.urls import reverse
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

def index(request):
    return HttpResponse("Hello, world. You're at the member index.")

class DetailView(generic.DetailView):
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

        return context


class UpdateView(BaseUpdateView):
    model = Member
    fields = ['email','username','nickname','phone','statement','images']
    def get_success_url(self):
        return reverse('member-detail', kwargs={'pk': self.object.id})

class PreferencesUpdateView(BaseUpdateView):
    model = MemberPreferences
    fields = ['hide_canceled_gigs','locale','share_profile','share_email','calendar_show_only_confirmed', 
              'calendar_show_only_committed']
    def get_success_url(self):
        return reverse('member-detail', kwargs={'pk': self.object.id})


class AssocsView(LoginRequiredMixin, TemplateView):
    template_name='member/member_assocs.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assocs'] = Assoc.objects.select_related('band').filter(member__id = self.kwargs['pk'])
        context['the_colors'] = ['white', 'red', 'black'] # todo fix colors
        return context


class OtherBandsView(LoginRequiredMixin, TemplateView):
    template_name='member/member_band_popup.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bands'] = Band.objects.exclude(assocs__in=Assoc.objects.filter(member__id=self.kwargs['pk']))
        return context
