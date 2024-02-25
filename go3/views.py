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

from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.template.response import TemplateResponse


def error404(request, exception):
    data = {"error": "404"}
    return render(request, "base/error.html", data, status=404)


def error500(request):
    data = {"error": "500"}
    return render(request, "base/error.html", data, status=500)


class TemplateResponse404(TemplateResponse):
    status_code = 404


class test404(TemplateView):
    response_class = TemplateResponse404
    template_name = "base/error.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["error"] = 404
        return context
