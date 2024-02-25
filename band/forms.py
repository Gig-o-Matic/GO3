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
from .models import Band
import pytz


class BandForm(forms.ModelForm):
    def __init__(self, **kwargs):
        super().__init__(label_suffix="", **kwargs)

    class Meta:
        model = Band
        fields = [
            "name",
            "shortname",
            "hometown",
            "description",
            "member_links",
            "website",
            "new_member_message",
            "thumbnail_img",
            "images",
            "timezone",
            "default_language",
            "anyone_can_create_gigs",
            "anyone_can_manage_gigs",
            "share_gigs",
            "send_updates_by_default",
            "rss_feed",
            "simple_planning",
            "plan_feedback",
        ]

        widgets = {
            "images": forms.Textarea(
                attrs={"placeholder": "put urls to images on their own lines..."}
            ),
        }
