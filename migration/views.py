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
from .forms import BandMigrationForm, GigMigrationForm
from band.models import Band
from gig.models import Gig
from member.models import Member
from django.views.generic.base import TemplateView
from io import StringIO
import csv
import json
import dateutil.parser

def cast_bool(text):
    return text.lower() == "true"

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
            fieldnames = ['band_name', 'name', 'email', 'is_admin', 'section1', 'section2', 'section3']
            reader = csv.DictReader(StringIO(form.cleaned_data["paste"]), fieldnames, dialect='excel-tab')

            migration_messages = []
            for row in reader:
                band, band_created = Band.objects.get_or_create(name=row["band_name"])
                if band_created: migration_messages.append(f"Created new band {band.name}")

                member, member_created = Member.objects.get_or_create(email=row["email"], defaults={"username": row["name"]})
                if member_created:
                    async_task("migration.helpers.send_migrated_user_password_reset", band.id, member.id)

                is_admin = cast_bool(row["is_admin"])
                if row["section1"] and row["section1"] != "None":
                    imported_section_name = row["section1"]
                else:
                    imported_section_name = "No Section"
                default_section, _section_created = band.sections.get_or_create(name=imported_section_name)
                is_multisectional = bool(row["section2"] or row["section3"])
                _assoc, assoc_created = band.assocs.get_or_create(member=member, defaults={"is_admin": is_admin, "default_section": default_section, "is_multisectional": is_multisectional})
                if assoc_created:
                    migration_messages.append(f"Associated {member.username} ({member.email}) with {band.name} - {default_section.name} {'as band admin' if is_admin else ''}")
                else:
                    migration_messages.append(f"{member.username} ({member.email}) already present in {band.name}; skipping.")
            
            context = super().get_context_data(**kwargs)
            context["migration_messages"] = migration_messages
            context["return_to"] = "gig_migration_form"
            return self.render_to_response(context)

class GigMigrationFormView(SuperUserRequiredMixin, TemplateView):
    template_name = "migration/gig_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = GigMigrationForm()
        return context

class GigMigrationResultsView(SuperUserRequiredMixin, TemplateView):
    template_name = "migration/results.html"

    def post(self, request, *args, **kwargs):
        form = GigMigrationForm(request.POST)
        if form.is_valid():
            data = json.loads(form.cleaned_data["paste"])
            band = Band.objects.get(id=form.cleaned_data["band_id"])
            migration_messages = []
            for record in data:
                fields = record["fields"]
                gig = Gig(
                    band = band,
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
                    date = dateutil.parser.isoparse(fields["date"]),
                    setdate = dateutil.parser.isoparse(fields["setdate"]),
                    enddate = dateutil.parser.isoparse(fields["enddate"]),
                    created_date = dateutil.parser.isoparse(fields["created_date"]),
                )
                gig.save()
                migration_messages.append(f"Imported {gig.title}")


            context = super().get_context_data(**kwargs)
            context["migration_messages"] = migration_messages
            context["return_to"] = "gig_migration_form"
            return self.render_to_response(context)
