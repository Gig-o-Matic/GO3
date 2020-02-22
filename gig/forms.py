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
from .models import Gig
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class GigForm(forms.ModelForm):
    def __init__(self, **kwargs):
        super().__init__(
            label_suffix='',
            **kwargs
        )

    def clean_date(self):
        date = self.cleaned_data['date']
        if date < timezone.now():
            raise ValidationError(_('Date must be in the future'), code='invalid date')
        return date

    def clean_setdate(self):
        date = self.cleaned_data['date']
        setdate = self.cleaned_data['setdate']
        if setdate and setdate < date:
            raise ValidationError(_('Set date must be later than the start date'), code='invalid end date')
        return date

    def clean_enddate(self):
        date = self.cleaned_data['date']
        enddate = self.cleaned_data['enddate']
        if enddate and enddate < date:
            raise ValidationError(_('End date must be later than the start date'), code='invalid end date')
        return date

    class Meta:
        model = Gig
        fields = ['title','contact','status','is_private','date','setdate','enddate','address','dress','paid','postgig',
                'details','setlist','rss_description','invite_occasionals','hide_from_calendar']

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': _('required')}),
        }
