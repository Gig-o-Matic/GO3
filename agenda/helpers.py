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

from go3.colors import the_colors
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.paginator import Paginator


PAGE_LENGTH = 10

@login_required
def agenda_gigs(request, the_type=None, page=1):

    if the_type == 'noplans':
        the_plans = request.user.future_noplans.all()
    else:
        the_plans = request.user.future_plans.all()

    paginator = Paginator(the_plans, PAGE_LENGTH)
    page_obj = paginator.get_page(page)

    return render(request, 'agenda/agenda_gigs.html', {'the_colors:': the_colors, 'page_obj': page_obj, 'the_type':the_type})

