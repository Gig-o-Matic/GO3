from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from django.contrib.auth.models import User
from member.models import Member
from django.utils.translation import gettext, gettext_lazy as _

# # Define an inline admin descriptor for Employee model
# # which acts a bit like a singleton
# class MemberInline(admin.StackedInline):
#     model = Member
#     can_delete = False
#     verbose_name_plural = 'member'

# # Define a new User admin
# class UserAdmin(BaseUserAdmin):
#     inlines = (MemberInline,)

# # Re-register UserAdmin
# admin.site.unregister(User)
# admin.site.register(User, UserAdmin)

class MemberAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('username', 'nickname')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = ('email', 'username', 'nickname',)
    list_filter = ()
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username','nickname')}),
    )
  
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ()

admin.site.register(Member, MemberAdmin)