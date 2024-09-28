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

# Register your models here.

from .models import Band, Assoc, Section

@admin.register(Band)
class BandAdmin(admin.ModelAdmin):
    search_fields=['name']
    readonly_fields = ("creation_date","last_activity",)

@admin.register(Assoc)
class AssocAdmin(admin.ModelAdmin):
    search_fields=['member__username', 'member__nickname', 'member__email', 'band__name']
    list_filter = ('is_admin',)

admin.site.register(Section)

