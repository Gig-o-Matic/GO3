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

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Plan

@login_required
def update_plan(request, pk, val):
    """ set value of plan """
    plan = Plan.objects.get(id=pk)
    plan.status = val
    plan.save()
    return HttpResponse()

@login_required
def update_plan_feedback(request, pk, val):
    """ set value of plan """
    plan = Plan.objects.get(id=pk)
    plan.feedback_value = val
    plan.save()
    return HttpResponse()

@login_required
def update_plan_comment(request, pk):
    """ set value of plan """
    plan = Plan.objects.get(id=pk)
    plan.comment = request.POST['value']
    plan.save()
    return HttpResponse()

# @login_required
def update_plan_default_section(assoc):
    """
    the default section of the member assoc has changed, so update any plans that aren't overriding
    """
    Plan.objects.filter(assoc=assoc, plan_section=None).update(section=assoc.default_section)
