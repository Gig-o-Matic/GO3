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

from django.contrib import admin

class Go3AdminSite(admin.AdminSite):
    site_header = 'Gig-o-Matic Admin'

    def get_app_list(self, request, app_label=None):
        """ set a better order for apps in the admin page """

        if not app_label is None:
            return super().get_app_list(request, app_label)

        order = ['Band','Member','Gig', 'Motd']

        app_list = super().get_app_list(request, app_label)

        new_app_list = [None] * len(order)

        for a in app_list:
            try:
                i = order.index(a['name'])
                new_app_list[i] = a
            except ValueError:
                new_app_list.append(a)

        return new_app_list
 