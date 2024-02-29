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
from .forms import MigrationForm
from band.models import Band, Assoc
from member.models import Member
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView
from django.http import HttpResponse
from io import StringIO
import csv

import logging
logger = logging.getLogger(__name__)

def find_or_create_band(band_name):
    try:
        band = Band.objects.get(name=band_name)
        logger.info(f"Found band id {band.id} for {band_name}")
    except Band.DoesNotExist:
        band = Band(name=band_name)
        band.save()
        logger.info(f"Created band id {band.id} for {band_name}")
    return band

def find_or_create_member(email, name):
    try:
        member = Member.objects.get(email=email)
        logger.info(f"Found member id {member.id} for email {email}")
    except Member.DoesNotExist:
        member = Member(email=email)
        member.save()
        logger.info(f"Created member id {member.id} for email {email}")
    return member

def find_or_create_assoc(band, member, is_admin):
    try:
        assoc = band.assocs.get(member=member)
        logger.info(f"Found existing association between member and band; skipping")
    except Assoc.DoesNotExist:
        assoc = band.assocs.create(member=member, is_admin=cast_bool(is_admin))
        logger.info(f"Added member to band as admin({is_admin})")

def cast_bool(bool):
    return bool.lower() == "true"

class MigrationFormView(LoginRequiredMixin, TemplateView):
    template_name = 'migration/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Migration Form"
        context["form"] = MigrationForm()
        return context

    def post(self, request, *args, **kwargs):
        form = MigrationForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            fieldnames = ['band_name', 'name', 'email', 'is_admin', 'section1', 'section2', 'section3']
            reader = csv.DictReader(StringIO(form.cleaned_data["paste"]), fieldnames, dialect='excel-tab')

            for row in reader:
                band = find_or_create_band(row['band_name'])
                member = find_or_create_member(row['email'], row['name'])
                find_or_create_assoc(band, member, row['is_admin'])
            return HttpResponse(status=200)

    



