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
from gig.models import Gig
from django.utils import timezone
from datetime import timedelta

def delete_old_trashed_gigs():
    """
    Deletes gigs that were tashed more than 30 days ago
    """

    cutoff = timezone.now() - timedelta(days=30)
    old_trash = Gig.objects.filter(trashed_date__lt=cutoff)
    num = old_trash.count()
    old_trash.delete()
    return f'deleted {num} old trashed gigs'
    
    