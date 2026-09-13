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
from django.utils.translation import gettext_lazy as _
from .models import Band

class BandForm(forms.ModelForm):
    def __init__(self, **kwargs):
        super().__init__(
            label_suffix='',
            **kwargs
        )

    def clean(self):
        super().clean()
        site = self.cleaned_data.get('website',None)
        if site:
            if len(site) >= 4 and not site[0:4] == 'http':
                self.cleaned_data['website'] = 'http://'+site

    class Meta:
        model = Band
        fields = ['name', 'shortname', 'hometown', 'description', 'member_links', 'website',
            'new_member_message', 'thumbnail_img', 'images', 'default_language', 'timezone',
            'anyone_can_create_gigs', 'anyone_can_manage_gigs', 'share_gigs',
            'send_updates_by_default', 'invite_occasionals_by_default', 'simple_planning', 'plan_feedback']

        widgets = {
            'images': forms.Textarea(attrs={'placeholder': 'put urls to images on their own lines...'}),
        }

        labels = {
            'name': _('Band Name'),
            'shortname': _('Short Name'),
            'hometown': _('Hometown'),
            'description': _('About the Band'),
            'member_links': _('Useful Links for Members'),
            'website': _('Band Website'),
            'new_member_message': _('Message for New Member Emails'), 
            'thumbnail_img': _('Thumbnail Image'), 
            'images': _('Band Images'), 
            'default_language': _('Language'), 
            'timezone':_('Timezone'),
            'anyone_can_create_gigs': _('Anyone Can Create Gigs'), 
            'anyone_can_manage_gigs': _('Anyone Can Manage Gigs'), 
            'share_gigs': _('Show Gigs On Public Page'),
            'send_updates_by_default': _('Send Gig Updates By Default'), 
            'invite_occasionals_by_default': _('Invite Occasional Members By Default'), 
            'simple_planning': _('Use Yes/Maybe/No Responses'), 
            'plan_feedback': _('Use Additional Feedback Options'),
        }
