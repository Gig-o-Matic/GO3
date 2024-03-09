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
from django import forms
from band.models import Band

class BandMigrationForm(forms.Form):
    paste = forms.CharField(label="Paste", widget=forms.Textarea)
    tzlist = [
        "America/New_York",
        "America/Chicago",
        "America/Denver",
        "America/Los_Angeles",
        "UTC",
    ]
    timezone = forms.ChoiceField(label="Timezone", choices=[[tz, tz] for tz in tzlist])

class GigMigrationForm(forms.Form):
    paste = forms.CharField(label="Paste", widget=forms.Textarea)
    band_id = forms.ChoiceField(label="Band", choices=(lambda: [[b.id, b.name] for b in Band.objects.filter(gigs__isnull=True)]))