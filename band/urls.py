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
    path("", views.BandList.as_view(), name="band-nav"),
    path("<int:pk>/", views.DetailView.as_view(), name="band-detail"),
    path("<int:pk>/update/", views.UpdateView.as_view(), name="band-update"),
    path("<int:pk>/members/", views.AllMembersView.as_view(), name="all-members"),
    path("<int:pk>/stats/", views.BandStatsView.as_view(), name="band-stats"),
    path(
        "<int:pk>/section/<int:sk>",
        views.SectionMembersView.as_view(),
        name="section-members",
    ),
    path(
        "<int:pk>/member_spreadsheet",
        views.member_spreadsheet,
        name="member-spreadsheet",
    ),
    path("<int:pk>/member_emails", views.member_emails, name="member-emails"),
    path("<int:pk>/trashcan", views.TrashcanView.as_view(), name="band-trashcan"),
    path("<int:pk>/archive", views.ArchiveView.as_view(), name="band-archive"),
    path(
        "<int:pk>/sections", views.SectionSetupView.as_view(), name="band-section-setup"
    ),
    path("<int:pk>/set_sections", helpers.set_sections, name="band-set-sections"),
    path("pub/<str:name>/", helpers.band_public_page, name="band-public-page"),
    path("assoc/<int:ak>/tfparam", helpers.set_assoc_tfparam, name="assoc-tfparam"),
    path(
        "assoc/<int:ak>/color/<int:colorindex>",
        helpers.set_assoc_color,
        name="assoc-color",
    ),
    path(
        "assoc/<int:ak>/section/<int:sk>",
        helpers.set_assoc_section,
        name="assoc-section",
    ),
    path("<int:bk>/join/<int:mk>", helpers.join_assoc, name="assoc-join"),
    path("assoc/<int:ak>/confirm", helpers.confirm_assoc, name="assoc-confirm"),
    path("assoc/<int:ak>/delete", helpers.delete_assoc, name="assoc-delete"),
    path("assoc/<int:ak>/rejoin", helpers.rejoin_assoc, name="assoc-rejoin"),
    path("calfeed/<uuid:pk>", helpers.band_calfeed, name="band-calfeed"),
]
