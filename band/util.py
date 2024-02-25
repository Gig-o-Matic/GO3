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


class BandStatusChoices(models.IntegerChoices):
    ACTIVE = 0, "Active"
    DORMANT = 1, "Dormant"
    DELETED = 2, "Deleted"


class AssocStatusChoices(models.IntegerChoices):
    NOT_CONFIRMED = 0, "Not Confirmed"
    CONFIRMED = 1, "Confirmed"
    INVITED = 2, "Invited"
    ALUMNI = 3, "Alumni"
    PENDING = 4, "Pending"
