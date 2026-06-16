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

from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from .middleware import FIREWALL_STATS

def superuser_required(func):
    def decorated(request, *args, **kw):
        if not (request.user.is_superuser):
            return HttpResponseForbidden()
        return func(request, *args, **kw)
    return decorated

@login_required
@superuser_required
def reset_firewall_stats(request):
    FIREWALL_STATS['filtered files'] = 0
    FIREWALL_STATS['404 paths'] = {}
    return HttpResponseRedirect('/admin/firewall')
