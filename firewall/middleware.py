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
from collections import OrderedDict
from django.http import HttpResponseForbidden
from go3.settings import START_FIREWALL
from python_ipware import IpWare


BAD_FILE_EXTENSIONS = ['php','env','tar','sql','xml','zip']
BAD_FILE_PREFIXES = ['/wp-admin', '/apple-touch-icon', '/wp-includes', 
                     '/.well-known,']
PROBATION_LIMIT = 30
BLACKLIST_LIMIT = 300

class FirewallMiddleware:

    firewall_on = START_FIREWALL
    blacklisted_requests = 0
    filtered_files = 0
    blacklist_ips = {}
    probation_ips = OrderedDict()
    last_reset = datetime.now()
    alltime_blacklist_ips = []

    ipw = IpWare()

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if self.firewall_on:

            # are we blacklisted?
            ip = self.get_user_ip(request)

            if ip in self.blacklist_ips:
                time_in_list = datetime.now() - self.blacklist_ips[ip]
                if time_in_list.seconds < BLACKLIST_LIMIT:
                    return HttpResponseForbidden()
                else:
                    self.blacklist_ips.pop(ip)


            # check for files that should not be requested
            file_extension = request.path.split('/')[-1].split('.')[-1].strip()
            if file_extension and file_extension in BAD_FILE_EXTENSIONS:
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
            # did we get a 404? If so, see if this ip is messing with up
            if response.status_code == 404:
                if ip in self.probation_ips:
                    self.probation_ips[ip].append([datetime.now()])
                    if len(self.probation_ips[ip]) > 2:
                        time_since_first = datetime.now() - self.probation_ips[ip][0]
                        if time_since_first.seconds < PROBATION_LIMIT:
                            self.probation_ips.pop(ip)
                            self.blacklist_ips[ip] = datetime.now()
                            self.blacklisted_requests += 1
                            self.alltime_blacklist_ips.append(ip)
                            if len(self.alltime_blacklist_ips) > 200:
                                self.alltime_blacklist_ips.pop(0)
                            self.blacklisted_requests += 1
                            return HttpResponseForbidden()
                        else:
                            # just pop the first one
                            self.probation_ips[ip] = self.probation_ips[1:]
                else:
                    self.probation_ips[ip] = [datetime.now()]
            elif ip in self.probation_ips:
                # they made an OK request, they're off probation
                self.probation_ips.pop(ip)

        return response

    def reset(self):
        self.blacklisted_requests = 0
        self.filtered_files = 0
        self.blacklist_ips = {}
        self.probation_ips = OrderedDict()
        self.last_reset = datetime.now()
        self.alltime_blacklist_ips = []


    def get_user_ip(self, request):
        # x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        # if x_forwarded_for:
        #     ip = x_forwarded_for.split(',')[0].strip()
        # else:
        #     ip = request.META.get('REMOTE_ADDR')
        # return ip
        ip, _ = self.ipw.get_client_ip(request.META)
        return ip
