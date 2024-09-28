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

from django.contrib import admin
from .models import Gig, Plan

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    search_fields=['assoc__member__username', 'assoc__member__nickname', 'assoc__member__email', 'gig__band__name', 'gig__title']

@admin.register(Gig)
class GigAdmin(admin.ModelAdmin):
    search_fields=['title', 'band__name']
    readonly_fields = (['created_date'])

