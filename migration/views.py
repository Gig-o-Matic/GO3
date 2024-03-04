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
from .forms import MigrationForm
from band.models import Band
from member.models import Member
from django.views.generic.base import TemplateView
from io import StringIO
import csv

import logging
logger = logging.getLogger(__name__)

def cast_bool(bool):
    return bool.lower() == "true"

class MigrationFormView(SuperUserRequiredMixin, TemplateView):
    template_name = "migration/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = MigrationForm()
        return context

class MigrationResultsView(SuperUserRequiredMixin, TemplateView):
    template_name = "migration/results.html"

    def post(self, request, *args, **kwargs):
        form = MigrationForm(request.POST)
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
                is_multisectional = True if (row["section2"] or row["section3"]) else False
                _assoc, assoc_created = band.assocs.get_or_create(member=member, defaults={"is_admin": is_admin, "default_section": default_section, "is_multisectional": is_multisectional})
                if assoc_created:
                    migration_messages.append(f"Associated {member.username} ({member.email}) with {band.name} - {default_section.name} {'as band admin' if is_admin else ''}")
                else:
                    migration_messages.append(f"{member.username} ({member.email}) already present in {band.name}; skipping.")
            
            context = super().get_context_data(**kwargs)
            context["migration_messages"] = migration_messages
            return self.render_to_response(context)

        



