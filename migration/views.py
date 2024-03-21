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
from django_q.tasks import async_task
from lib.mixins import SuperUserRequiredMixin
from .forms import BandMigrationForm
from band.models import Band
from band.util import AssocStatusChoices
from gig.models import Gig
from member.models import Member
from django.views.generic.base import TemplateView
from io import StringIO
import csv
import json
import dateutil.parser
import pytz
import re

class BandMigrationFormView(SuperUserRequiredMixin, TemplateView):
    template_name = "migration/band_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = BandMigrationForm()
        return context

class BandMigrationResultsView(SuperUserRequiredMixin, TemplateView):
    template_name = "migration/results.html"

    def post(self, request, *args, **kwargs):
        form = BandMigrationForm(request.POST)
        if form.is_valid():
            data = json.loads(form.cleaned_data["paste"])
            
            migration_messages = []

            # Extract sections, we'll associate these in a sec
            section_list = data['band'].pop('sections')

            # Transform the list of images into how they are stored
            data['band']['images'] = "\n".join(data['band'].pop('images'))

            # Delete internal and unimplemented attributes
            del data['band']['band_cal_feed_dirty']
            del data['band']['pub_cal_feed_dirty']
            del data['band']['show_in_nav']

            band, band_created = Band.objects.get_or_create(name=data['band']['name'], defaults=data['band'])
            if band_created:
                migration_messages.append(f"Created new band {band.name}")
            else:
                migration_messages.append(f"Band {data['band']['name']} already in DB")
            for section_name in section_list:
                section, section_created = band.sections.get_or_create(name=section_name)
                if section_created:
                    migration_messages.append(f"Created new section {section.name}")
                else:
                    migration_messages.append(f"Section {section.name} already in DB")
                
            for member_data in data['members']:   
                is_admin = member_data.pop('is_admin')
                is_occasional = member_data.pop('is_occasional')
                section_name=member_data.pop('section')
                if section_name:
                    section = band.sections.get(name=section_name)
                else:
                    section = band.sections.get(name="No Section")

                member_data['go2_id'] = member_data.pop('old ID')

                member, member_created = Member.objects.get_or_create(email=member_data["email"], defaults=member_data)
                if member_created:
                    async_task("migration.helpers.send_migrated_user_password_reset", band.id, member.id)
                    migration_messages.append(f"Created new member {member.email}")

                _assoc, assoc_created = band.assocs.get_or_create(member=member, defaults={"is_admin": is_admin, "default_section": section, "is_occasional": is_occasional, "status": AssocStatusChoices.CONFIRMED})
                if assoc_created:
                    migration_messages.append(f"Associated {member.email} with {band.name} - {section.name} {'as band admin' if is_admin else ''}")
                else:
                    migration_messages.append(f"{member.username} ({member.email}) already present in {band.name}; skipping.")
            
            admin = band.assocs.filter(is_admin=True).first().member
            for gig_data in data['gigs']:
                fields = gig_data['fields']
                gig = Gig(
                    band = band,
                    contact = admin,
                    title = fields["title"],
                    details = fields["details"],
                    setlist = fields["setlist"],
                    address = fields["address"],
                    dress = fields["dress"],
                    paid = fields["paid"],
                    postgig = fields["postgig"],
                    is_private = fields["is_private"],
                    is_archived = fields["is_archived"],
                    invite_occasionals = fields["invite_occasionals"],
                    was_reminded = fields["was_reminded"],
                    hide_from_calendar = fields["hide_from_calendar"],
                    rss_description = fields["rss_description"],
                    default_to_attending = fields["default_to_attending"],
                    date = self.mangle_time(fields["date"], band.timezone),
                    setdate = self.mangle_time(fields["setdate"], band.timezone),
                    enddate = self.mangle_time(fields["enddate"], band.timezone),
                    created_date = self.mangle_time(fields["created_date"], band.timezone),
                    datenotes = fields["time_notes"],
                )
                gig.save()
                migration_messages.append(f"Added gig {gig.title}")
            context = super().get_context_data(**kwargs)
            context["migration_messages"] = migration_messages
            context["return_to"] = "gig_migration_form"
            return self.render_to_response(context)

    def mangle_time(self, timestr, tzstr):
        # Necessary because GO2 was not tz-aware
        # Interpret the time in the band's zone
        tz = pytz.timezone(tzstr)
        stripped = re.sub("\\+00:00", "", timestr)
        parsed = dateutil.parser.isoparse(stripped)
        return tz.localize(parsed)

