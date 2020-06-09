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


@login_required
def agenda_gigs(request, type=None, max=None):

    the_plans=[]

    if type == 'noplans':
        the_plans = request.user.future_noplans.all()
    else:
        if max:
            the_plans = request.user.future_plans.all()[:max]
        else:
            the_plans = request.user.future_plans.all()

    return render(request, 'agenda/agenda_gigs.html', {'the_colors:': the_colors, 'the_plans': the_plans})
