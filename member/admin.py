from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm
# from django.contrib.auth.models import User
from .models import Member, MemberPreferences

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
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Other stuff', {'classes': ('collapse',),
                         'fields': ('statement', 'seen_motd_time', 'seen_welcome', 
                                    'show_long_agenda', 'images', 'cal_feed_dirty',
                                    )}),
    )

    inlines = [
        PreferencesInline,
    ]

    add_form = MemberCreateForm

    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ()

admin.site.register(Member, MemberAdmin)
admin.site.register(MemberPreferences)