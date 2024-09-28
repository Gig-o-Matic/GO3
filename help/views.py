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
from member.models import Member
from django.shortcuts import render, redirect
from django.views.generic.edit import FormView
from django.views.generic.base import TemplateView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import BandRequestForm
from lib import email
from lib.captcha import verify_captcha, get_captcha_site_key
from go3.settings import env, URL_BASE, SUPERUSER_EMAIL, HELP_EMAIL

@login_required
def help(request):
    return render(request, 'help/help.html', {'superuser_email':SUPERUSER_EMAIL})

@login_required
def privacy(request):
    return render(request, 'help/privacy.html')

@login_required
def credits(request):
    return render(request, 'help/credits.html')

@login_required
def changelog(request):
    return render(request, 'help/changelog.html')

class CalfeedView(LoginRequiredMixin, TemplateView):
    template_name = 'help/calfeed.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        member = Member.objects.get(id=self.kwargs['pk'])
        context['member'] = member
        context['url_base'] = URL_BASE
        return context


def whatis(request):
    return render(request, 'help/whatis.html', {'help_email':HELP_EMAIL})

class BandRequestView(FormView):
    template_name = 'help/band_request.html'
    form_class = BandRequestForm

    def get_context_data(self, **kw):
        context = super().get_context_data(**kw)
        context['site_key'] = get_captcha_site_key()
        context['enable_captcha'] = env("CAPTCHA_ENABLE", default=True)
        return context

    def form_valid(self, form):
        # first check the captcha
        if not verify_captcha(self.request):
            return redirect('home')

        recipient = email.EmailRecipient(email=SUPERUSER_EMAIL)
        message = email.prepare_email(recipient, 'email/band_request.md', form.cleaned_data)
        email.send_messages_async([message])
        return render(self.request, 'help/confirm_band_request.html')
