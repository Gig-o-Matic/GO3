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

"""go3 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""


from django.contrib import admin
from django.urls import include, path
from graphene_django.views import GraphQLView
from .views import error404, error500, test404
from .tasks import do_daily_tasks, do_hourly_tasks
from go3.schema import schema
from agenda.views import PrivateGraphQLView

urlpatterns = [
    path("", include("agenda.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("i18n/", include("django.conf.urls.i18n")),
    path("band/", include("band.urls")),
    path("member/", include("member.urls")),
    path("gig/", include("gig.urls")),
    path("help/", include("help.urls")),
    path("stats/", include("stats.urls")),
    path("admin/", admin.site.urls),
    path("graphql", PrivateGraphQLView.as_view(graphiql=True, schema=schema)),
    path("tasks/hourly", do_hourly_tasks),
    path("tasks/daily", do_daily_tasks),
    path("404", test404.as_view()),
]

handler404 = error404
handler500 = error500
