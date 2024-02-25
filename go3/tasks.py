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

from django_q.tasks import async_task
from django.conf import settings
from django.http import HttpResponse


def do_daily_tasks(request):
    if int(request.GET.get("key", 0)) == settings.ROUTINE_TASK_KEY:
        async_task("gig.tasks.delete_old_trashed_gigs")
        async_task("gig.tasks.archive_old_gigs")
        async_task("gig.tasks.send_snooze_reminders")
        async_task("stats.tasks.collect_band_stats")
        return HttpResponse("did it!")
    else:
        return HttpResponse()


def do_hourly_tasks(request):
    if int(request.GET.get("key", 0)) == settings.ROUTINE_TASK_KEY:
        async_task("member.tasks.update_all_calfeeds")
        async_task("band.tasks.update_all_calfeeds")
        return HttpResponse("did it!")
    else:
        return HttpResponse()
