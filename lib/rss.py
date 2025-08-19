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
from django.contrib.syndication.views import Feed
from django.utils import translation, timezone
from django.template.loader import render_to_string
from datetime import datetime, timedelta
import pytz
from band.models import Band
from gig.models import Gig, GigStatusChoices

class BandFeed(Feed):

    def get_object(self, request, pk):
        return Band.objects.get(pub_cal_feed_id=pk)

    def title(self, obj):
        return f'Gigs for {obj.name}'

    def link(self, obj):
        return obj.get_public_url()

    def description(self, obj):
        return f'Gigs for {obj.name}'

    def items(self, obj):
        threshold_date = timezone.now() - timedelta(hours=4)
        the_gigs = Gig.objects.filter(band=obj,
                                date__gt=threshold_date,
                                trashed_date__isnull=True,
                                is_archived=False,
                                is_private=False,
                                status=GigStatusChoices.CONFIRMED,
                            ).order_by('date')
        return the_gigs
    
    def item_link(self, item):
        return item.band.get_public_url()

    def item_title(self, item):
        with timezone.override(pytz.timezone(item.band.timezone)):
            with translation.override(item.band.default_language):
                title = render_to_string('rss/title.html', {'obj':item}).strip()
        return title

    def item_description(self, item):
        return item.public_description