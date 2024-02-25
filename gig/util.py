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


class PlanStatusChoices(models.IntegerChoices):
    NO_PLAN = 0, _("No Plan")
    DEFINITELY = 1, _("Definitely")
    PROBABLY = 2, _("Probably")
    DONT_KNOW = 3, _("Don't Know")
    PROBABLY_NOT = 4, _("Probably Not")
    CANT_DO_IT = 5, _("Can't Do It")
    NOT_INTERESTED = 6, _("Not Interested")


class GigStatusChoices(models.IntegerChoices):
    UNKNOWN = 0, _("Unknown")
    CONFIRMED = 1, _("Confirmed")
    CANCELLED = 2, _("Cancelled")
    ASKING = 3, _("Asking")
