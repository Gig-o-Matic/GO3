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

# A simple firewall middleware meant to ward off standard kinds of attacks
from django.http import HttpResponseForbidden
from go3.settings import FIREWALL_ON

BAD_FILE_EXTENSIONS = ['php','env']
BAD_FILE_PREFIXES = ['/wp-admin', '/favicon.ico', '/apple-touch-icon']
PATH_404 = {}

class FirewallMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if FIREWALL_ON:
            # check for files that should not be requested
            file_extension = request.path.split('/')[-1].split('.')[-1].strip()
            if file_extension in BAD_FILE_EXTENSIONS:
                return HttpResponseForbidden()

            for pref in BAD_FILE_PREFIXES:
                if request.path.startswith(pref):
                    return HttpResponseForbidden()

        response = self.get_response(request)


        if FIREWALL_ON:
            # did we get a 404? If so, remember what it was
            if response.status_code == 404:
                if request.path in PATH_404:
                    PATH_404[request.path] += 1
                else:
                    PATH_404[request.path] = 1

        return response
