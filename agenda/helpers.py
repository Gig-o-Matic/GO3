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


PAGE_LENGTH = 10

@login_required
def agenda_gigs(request, type=None, page=1):

    the_type=request.path.split('/')[1]

    the_plans=[]

    first = (page - 1) * PAGE_LENGTH
    last = first + PAGE_LENGTH

    if the_type == 'noplans':
        the_plans = request.user.future_noplans.all()
    else:
        the_plans = request.user.future_plans.all()

    if (page * PAGE_LENGTH) < the_plans.count():
        next_page = page + 1
    else:
        next_page = 0

    the_plans = the_plans[first:last]

    return render(request, 'agenda/agenda_gigs.html', {'the_colors:': the_colors, 'the_plans': the_plans, 'list_url': f'agenda-gigs-{the_type}', 'nextpage':next_page})

@login_required
def toggle_view(request):
    request.user.preferences.show_long_agenda = not request.user.preferences.show_long_agenda
    request.user.preferences.save()
    return agenda_gigs(request, type='plans')
