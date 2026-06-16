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
from datetime import datetime
from django.http import HttpResponseForbidden
from go3.settings import START_FIREWALL
from python_ipware import IpWare


BAD_FILE_EXTENSIONS = ['php','env']
BAD_FILE_PREFIXES = ['/wp-admin', '/favicon.ico', '/apple-touch-icon']

class FirewallMiddleware:

    firewall_on = START_FIREWALL
    filtered_files = 0
    paths_404 = {}
    ips_404 = {}
    last_reset = datetime.now()

    ipw = IpWare()

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if self.firewall_on:
            # check for files that should not be requested
            file_extension = request.path.split('/')[-1].split('.')[-1].strip()
            if file_extension in BAD_FILE_EXTENSIONS:
                self.filtered_files += 1
                return HttpResponseForbidden()

            for pref in BAD_FILE_PREFIXES:
                if request.path.startswith(pref):
                    self.filtered_files += 1
                    return HttpResponseForbidden()

        if request.path.startswith('/admin/firewall/') or request.path.startswith('/firewall/'):
            request.firewall = self # pass this on the request so it can be used later
        response = self.get_response(request)

        if self.firewall_on:
            # did we get a 404? If so, remember what it was
            if response.status_code == 404:
                if request.path in self.paths_404:
                    self.paths_404[request.path] += 1
                else:
                    self.paths_404[request.path] = 1

                    while len(self.paths_404)>200:
                        # just drop some
                        self.paths_404.popitem()

                ip = self.get_user_ip(request)
                if ip in self.ips_404:
                    self.ips_404[ip] += 1
                else:
                    self.ips_404[ip] = 1

                while len(self.ips_404)>200:
                    # just drop some
                    self.ips_404.popitem()

        return response

    def reset(self):
        self.filtered_files = 0
        self.paths_404 = {}
        self.ips_404 = {}
        self.last_reset = datetime.now()


    def get_user_ip(self, request):
        # x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        # if x_forwarded_for:
        #     ip = x_forwarded_for.split(',')[0].strip()
        # else:
        #     ip = request.META.get('REMOTE_ADDR')
        # return ip
        ip, _ = self.ipw.get_client_ip(request.META)
        return ip