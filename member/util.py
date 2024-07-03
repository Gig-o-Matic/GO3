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
from django.db import models
from django.utils.translation import gettext_lazy as _

class MemberStatusChoices(models.IntegerChoices):
    ACTIVE = 0, "Active"
    DORMANT = 1, "Dormant"
    DELETED = 2, "Deleted"

class AgendaChoices(models.IntegerChoices):
    AGENDA = 0, "Agenda"
    GRID = 1, "Grid"
    CALENDAR = 2, "Calendar"

class AgendaLayoutChoices(models.IntegerChoices):
    NEED_RESPONSE = 0, _("Weigh In")
    BY_BAND = 1, _("By Band")
    ONE_LIST = 2, _("Single List")

# # Types of panels for the agenda page. Any other value is the ID of a band to show
# class AgendaPanelTypes(models.IntegerChoices):
#     HAS_RESPONSE = 0, "Has Response"
#     NEEDS_RESPONSE = 1, "Needs Response"
#     ONE_LIST = 2, "Entire List"
#     ONE_BAND = 3, "Single Band"
