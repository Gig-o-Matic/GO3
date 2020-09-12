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
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm
# from django.contrib.auth.models import User
from .models import Member, MemberPreferences, Invite

class MemberCreateForm(UserCreationForm):
    class Meta:
        model = Member
        fields = ('email', 'username')

class PreferencesInline(admin.StackedInline):
    model = MemberPreferences
    classes = ['collapse']
    verbose_name_plural = "Preferences"

class MemberAdmin(BaseUserAdmin):
    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.

    list_display = ('email', 'username', 'nickname')
    list_filter = ()
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username','nickname','phone')}),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Other stuff', {'classes': ('collapse',),
                         'fields': ('statement', 'motd_dirty', 'seen_welcome', 
                                    'images', 'cal_feed_dirty',
                                    )}),
    )

    inlines = [
        PreferencesInline,
    ]

    def get_inlines(self, request, obj):
        """Hook for specifying custom inlines."""
        if obj:
            return self.inlines
        else:
            return []

    add_form = MemberCreateForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username','password1', 'password2'),
        }),
    )
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ()

admin.site.register(Member, MemberAdmin)
admin.site.register(MemberPreferences)
admin.site.register(Invite)
