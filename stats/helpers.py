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

from .models import BandMetric, Stat
from band.models import Band

def get_band_stats(the_band):
    """ return the stats that exist for a band """

    the_stats = {}

    the_metrics = BandMetric.objects.filter(band=the_band)
    for m in the_metrics:
        the_stat = m.stats.order_by('updated').last()
        the_stats[m.name] = {
            'date': the_stat.updated,
            'value': the_stat.value
        }
    return the_stats