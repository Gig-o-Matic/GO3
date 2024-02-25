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

from member.models import Member
from member.helpers import update_member_calfeed
from django_q.tasks import async_task
from django.conf import settings


def update_all_calfeeds():
    """request handler for updating cached calfeeds - should be called on a schedule"""

    if settings.DYNAMIC_CALFEED:
        return

    members = Member.objects.filter(cal_feed_dirty=True)
    for m in members:
        async_task(update_member_calfeed, m.id)
    members.update(cal_feed_dirty=False)
