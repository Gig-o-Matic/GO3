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

urlpatterns = [
    path("create/<int:bk>", views.CreateView.as_view(), name="gig-create"),
    path("<int:pk>/", views.DetailView.as_view(), name="gig-detail"),
    path("<int:pk>/update", views.UpdateView.as_view(), name="gig-update"),
    path("<int:pk>/comments", views.CommentsView.as_view(), name="gig-comments"),
    path("<int:pk>/duplicate", views.DuplicateView.as_view(), name="gig-duplicate"),
    path("<int:pk>/trash", helpers.gig_trash, name="gig-trash"),
    path("<int:pk>/untrash", helpers.gig_untrash, name="gig-untrash"),
    path("<int:pk>/archive", helpers.gig_archive, name="gig-archive"),
    path("<int:pk>/remind", helpers.gig_remind, name="gig-remind"),
    path(
        "<int:pk>/printallplans",
        views.PrintPlansView.as_view(),
        {"all": True},
        name="gig-print-all-plans",
    ),
    path(
        "<int:pk>/printconfirmedplans",
        views.PrintPlansView.as_view(),
        {"all": False},
        name="gig-print-confirmed-plans",
    ),
    path(
        "<int:pk>/printsetlist",
        views.PrintSetlistView.as_view(),
        name="gig-print-setlist",
    ),
    path("plan/<uuid:pk>/update/<int:val>", helpers.update_plan, name="plan-update"),
    path(
        "plan/<uuid:pk>/feedback/<int:val>",
        helpers.update_plan_feedback,
        name="plan-update-feedback",
    ),
    path(
        "plan/<uuid:pk>/comment",
        helpers.update_plan_comment,
        name="plan-update-comment",
    ),
    path(
        "plan/<uuid:pk>/section/<int:val>",
        helpers.update_plan_section,
        name="plan-update-section",
    ),
    path("answer/<uuid:pk>/<int:val>", views.answer, name="gig-answer"),
]
