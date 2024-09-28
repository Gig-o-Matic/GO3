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
from band.models import Band
from django.utils import timezone, formats
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import datetime
from pytz import timezone as tzone, utc
from django.utils.formats import get_format

class GigForm(forms.ModelForm):
    def __init__(self, **kwargs):
        band = kwargs.pop('band', None)
        user = kwargs.pop('user', None)

        super().__init__(
            label_suffix='',
            **kwargs
        )
        
        if band is None and self.instance.band_id is not None:
            # TODO more robust checking, this form without a band doesn't make sense
            band = self.instance.band

        instance = kwargs.get('instance',None)
        if instance is None:
            """ this is a new gig """
            self.fields['email_changes'].label = _('Email members about this new gig')
            self.fields['email_changes'].initial = band.send_updates_by_default
        else:
            self.fields['email_changes'].label = _('Email members about change')

        if user:
            self.fields['contact'].initial = user
            self.fields['contact'].empty_label = None

        if band:
            self.fields['contact'].queryset = band.confirmed_members

        if band:
            self.fields['timezone'].initial = band.timezone
        elif self.instance:
            self.fields['timezone'].initial = self.instance.band.timezone
        else:
            raise(ValueError('issue with band'))


    def clean(self):
        """
        Checks to make sure the dates and times are valid.
         
        if the gig is a full-or-multi-day event, the times are ignored.
        if the gig is not full-or-multi-day,
            if the times are there, they must be parsable
            if the times are good, they are merged into the datetime for date, set, calltime
            the appropriate flags are set to note which times are "real" in the datetimes.
        """
        def _parse(val,format_type):
            x = None
            if val:
                for format in get_format(format_type):
                    try:
                        x = datetime.strptime(val.replace(' ',''), format)
                    except (ValueError, TypeError):
                        continue
            return x

        def _mergetime(hour, minute='', zone=None):
            if minute:
                hour = hour.replace(hour=minute.hour, minute=minute.minute)
            return zone.localize(hour) if zone else hour

        date = _parse(self.cleaned_data.get('call_date'), 'DATE_INPUT_FORMATS')
        if date is None:
            self.add_error('call_date', ValidationError(_('Date is not valid'), code='invalid date'))
            super().clean()
            return
        
        # first, check to see if this is full-day or not
        if self.cleaned_data.get('is_full_day'):
            # we're full day, so see if there's an end date
            end_date = _parse(self.cleaned_data.get('end_date',''), 'DATE_INPUT_FORMATS')

            # since we are full day, ignore the times completely
            self.cleaned_data['has_call_time'] = False
            self.cleaned_data['has_set_time'] = False
            self.cleaned_data['has_end_time'] = False

            date = tzone(self.fields['timezone'].initial).localize(date)
            if end_date:
                end_date = tzone(self.fields['timezone'].initial).localize(end_date)

            self.cleaned_data['date'] = date
            self.cleaned_data['setdate'] = None
            self.cleaned_data['enddate'] = end_date

            if date < timezone.now():
                self.add_error('call_date', ValidationError(_('Gig date must be in the future'), code='invalid date'))
            if end_date and end_date < date:
                self.add_error('end_date', ValidationError(_('Gig end date must be later than the start date'), code='invalid date'))

        else:
            # we're not full-day, so ignore the end date in the form
            call_time = _parse(self.cleaned_data.get('call_time',None), 'TIME_INPUT_FORMATS')
            set_time = _parse(self.cleaned_data.get('set_time',None), 'TIME_INPUT_FORMATS')
            end_time = _parse(self.cleaned_data.get('end_time',None), 'TIME_INPUT_FORMATS')

            if not call_time:
                if set_time:
                    # if set time is set, but call time is not, default call time to match set time
                    call_time = set_time
                else:
                    # If call time and set time are both unset, treat this as a full-day gig (a gig without times)
                    self.cleaned_data['is_full_day'] = True

            self.cleaned_data['has_call_time'] = not call_time is None
            self.cleaned_data['has_set_time'] = not set_time is None
            self.cleaned_data['has_end_time'] = not end_time is None

            zone = tzone(self.fields['timezone'].initial)
            date = _mergetime(date, call_time, zone)
            setdate = _mergetime(date, set_time) if set_time else None
            enddate = _mergetime(date, end_time) if end_time else None

            if date < timezone.now():
                self.add_error('call_date', ValidationError(_('Gig call time must be in the future'), code='invalid date'))
            if setdate and setdate < date:
                self.add_error('set_time', ValidationError(_('Set time must not be earlier than the call time'), code='invalid set time'))
            if enddate:
                if enddate < date:
                    self.add_error('end_time', ValidationError(_('Gig end must not be earlier than the call time'), code='invalid end time'))
                elif setdate and enddate < setdate:
                    self.add_error('end_time', ValidationError(_('Gig end must not be earlier than the set time'), code='invalid end time'))

            self.cleaned_data['date'] = date
            self.cleaned_data['setdate'] = setdate
            self.cleaned_data['enddate'] = enddate

        super().clean()

    def save(self, commit=True):
        """ save our date, setdate, and enddate into the instance """
        self.instance.date = self.cleaned_data['date']
        self.instance.setdate = self.cleaned_data['setdate']
        self.instance.enddate = self.cleaned_data['enddate']
        newgig = super().save(commit)
        return newgig

    email_changes = forms.BooleanField(required=False, label=_('Email members about change'))
    is_full_day = forms.BooleanField(required=False, label=_('Full- or multi-day event'))
    call_date = forms.Field(required=True, label=_('Date'))
    call_time = forms.Field(required=False, label=_('Call Time'))
    set_time = forms.Field(required=False, label=_('Set Time'))
    end_time = forms.Field(required=False, label=_('End Time'))
    end_date = forms.Field(required=False, label=_('End Date'))
    timezone = forms.Field(required=False, widget=forms.HiddenInput())
    datenotes = forms.Field(required=False, label=_('Date Notes'))


    is_private = forms.BooleanField(required=False, label=_('Hide from public gig feed'))

    add_series = forms.BooleanField(required=False, label=_('Add A Series Of Copies'))
    total_gigs = forms.IntegerField(required=False, label=_('Total Number Of Gigs'), min_value=1, max_value=10)
    repeat = forms.ChoiceField(required=False, label=_('Repeat Every'), 
                                choices=[
                                            ('day', _('day')),
                                            ('week', _('week')),
                                            ('month', _('month (on same day of the month)')),
                                        ])


    class Meta:
        model = Gig
        localized_fields = '__all__'

        fields = ['title','contact','status','is_private','call_date','call_time','set_time','end_time','end_date', 
                'address','dress','paid','leader_text', 'postgig', 'details','setlist','rss_description','invite_occasionals',
                'hide_from_calendar','email_changes','add_series','total_gigs','datenotes','is_full_day','has_set_time',
                'has_call_time','has_end_time']

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': _('required')}),
            'address': forms.TextInput(attrs={'placeholder': _('Cloudcuckooland')}),
            'dress': forms.TextInput(attrs={'placeholder': _('Pants Optional')}),
            'paid': forms.TextInput(attrs={'placeholder': _('As If')}),
            'postgig': forms.TextInput(attrs={'placeholder': _('Hit the streets!')}),
            'details': forms.Textarea(attrs={'placeholder': _('who? what? where? when? why?')}),
            'setlist': forms.Textarea(attrs={'placeholder': _('setlist here')}),
            'leader_text': forms.TextInput(),
        }

        labels = {
            'title': _('Gig Title'),
            'contact': _('Contact'),
            'status': _('Status'),

            'is_full_day': _('Full- or Multi-day'),

            'call_date': _('Date'),
            'end_date': _('End Date'),

            'address': _('Address or URL'),
            'dress': _('What to Wear'),
            'paid': _('Pay Deal'),

            'leader_text': _('Leader'),
            'postgig': _('Post-gig Plans'),
            'details': _('Details'),
            'setlist': _('Setlist'),

            'hide_from_calendar': _('Hide from calendar'),
            'invite_occasionals': _('Include occasional members'),
            'email_changes': _('Email members about this new gig')
        }
