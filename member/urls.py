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

from django.urls import path
from . import views
from . import helpers
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView

urlpatterns = [
    path("", views.DetailView.as_view(), name="member-detail"),
    path("<int:pk>/", views.DetailView.as_view(), name="member-detail"),
    path("<int:pk>/update/", views.UpdateView.as_view(), name="member-update"),
    path(
        "<int:pk>/preferences/update/",
        views.PreferencesUpdateView.as_view(),
        name="member-prefs-update",
    ),
    path(
        "password-change/", PasswordChangeView.as_view(), name="member-password-change"
    ),
    path(
        "password-change/done/", views.DetailView.as_view(), name="password_change_done"
    ),
    path(
        "member-password-reset/",
        views.CaptchaPasswordResetView.as_view(),
        name="member-password-reset",
    ),
    path("<int:pk>/assocs/", views.AssocsView.as_view(), name="member-assocs"),
    path(
        "<int:pk>/otherbands/", views.OtherBandsView.as_view(), name="member-otherbands"
    ),
    path("send-test-email", helpers.send_test_email, name="member-test-email"),
    path("<int:pk>/motd_seen", helpers.motd_seen),
    path("calfeed/<uuid:pk>", helpers.calfeed, name="member-calfeed"),
    path("invite/<int:bk>", views.InviteView.as_view(), name="member-invite"),
    path("invite/<uuid:pk>", views.accept_invite, name="member-invite-accept"),
    path("invite/delete/<uuid:pk>", views.delete_invite, name="member-invite-delete"),
    path("create/<uuid:pk>", views.MemberCreateView.as_view(), name="member-create"),
    path("signup", views.SignupView.as_view(), name="member-signup"),
    path("email/<uuid:pk>", views.confirm_email, name="member-confirm-email"),
    path("<int:pk>/delete", helpers.delete_member, name="member-delete"),
]
