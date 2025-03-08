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
from gig.models import Gig, Plan
from gig.helpers import send_emails_from_plans, send_watcher_email
from member.models import Member
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Q
import pytz

def delete_old_trashed_gigs():
    """
    Deletes gigs that were trashed more than 30 days ago
    """
    cutoff = timezone.now() - timedelta(days=30)
    old_trash = Gig.objects.filter(trashed_date__lt=cutoff)
    num = old_trash.count()
    old_trash.delete()
    return f'deleted {num} old trashed gigs'
    
def archive_old_gigs():
    """
    Archived gigs that have passed more than 5 days ago (until then it's still editable)
    """
    archive_date = timezone.now() - timedelta(days=5)
    
    # find the gigs that:
    # - the enddate is None and the date has passed
    # - have an enddate and the enddate has passed

    over_gigs = Gig.objects.filter(
        (Q(enddate=None) & Q(date__lt=archive_date)) |
        (~Q(enddate=None) & Q(enddate__lt=archive_date)),
        is_archived=False)

    num = over_gigs.count()
    over_gigs.update(is_archived=True)
    return f'archived {num} gigs'

def send_snooze_reminders():
    """
    Send a reminder for all plans with a snooze_until in the next day and a gig
    date in the future.  Set the snooze_until property of all such plans to None,
    to so we don't send another reminder in the future.
    """
    now = datetime.now(tz=pytz.utc)
    next_day = now + timedelta(days=1)
    unsnooze = Plan.objects.filter(snooze_until__isnull=False,
                                   snooze_until__lte=next_day,
                                   gig__date__gt=now)
    send_emails_from_plans(unsnooze, 'email/gig_reminder.md')
    unsnooze.update(snooze_until=None)


def alert_watchers():
    """ alert members who are watching gigs that plans have changed """

    # first, get all the members who need to be alerted and tell them what's up
    members = set(Member.objects.filter(watching__isnull=False))

    for m in members:
        m_plans = Plan.objects.filter(status_changed=True, gig__in=m.watching.all())
        if m_plans:
            send_watcher_email(m, m_plans)

    # finally, mark the plans seen
    Plan.objects.all().update(status_changed=False)