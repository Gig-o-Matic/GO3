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
from datetime import datetime, timedelta
from pytz import timezone as tzone, utc
from django.utils.formats import get_format
import uuid
import calendar


class GigForm(forms.ModelForm):
    def __init__(self, **kwargs):
        band = kwargs.pop("band", None)
        user = kwargs.pop("user", None)

        super().__init__(label_suffix="", **kwargs)

        if kwargs.get("instance", None) is None:
            self.fields["send_update"].label = _("Email members about this new gig")
            self.fields["invite_occasionals"].label = _("Invite occasional members")
        else:
            self.fields["send_update"].label = _("Email members about change")
            self.fields["invite_occasionals"].label = _(
                "Also send update to occasional members"
            )

        if user:
            self.fields["contact"].initial = user
            self.fields["contact"].empty_label = None
        if band:
            self.fields["contact"].queryset = band.confirmed_members
            self.fields["leader"].queryset = band.confirmed_members

        if band:
            self.fields["timezone"].initial = band.timezone
        elif self.instance:
            self.fields["timezone"].initial = self.instance.band.timezone
        else:
            raise (ValueError("issue with band"))

        # self.fields['datenotes'].widget.attrs['style'] = 'width:100%;'

    def clean(self):
        """
        Checks to make sure the dates are valid. If there is an end-date set, it is assumed that the gig is "all day" events,
        so the times are not used. Otherwise the times are used and the enddate is just the same as the start date.
        """

        def _parse(val, format_type):
            x = None
            if val:
                for format in get_format(format_type):
                    try:
                        x = datetime.strptime(val.replace(" ", ""), format)
                    except (ValueError, TypeError):
                        continue
            return x

        def _mergetime(hour, minute="", zone=None):
            if minute:
                hour = hour.replace(hour=minute.hour, minute=minute.minute)
            return zone.localize(hour) if zone else hour

        date = _parse(self.cleaned_data.get("call_date"), "DATE_INPUT_FORMATS")
        if date is None:
            self.add_error(
                "call_date",
                ValidationError(_("Date is not valid"), code="invalid date"),
            )
            super().clean()
            return

        end_date = _parse(self.cleaned_data.get("end_date", ""), "DATE_INPUT_FORMATS")
        if end_date is None or end_date == date:
            call_time = _parse(
                self.cleaned_data.get("call_time", None), "TIME_INPUT_FORMATS"
            )
            set_time = _parse(
                self.cleaned_data.get("set_time", None), "TIME_INPUT_FORMATS"
            )
            end_time = _parse(
                self.cleaned_data.get("end_time", None), "TIME_INPUT_FORMATS"
            )

            date = _mergetime(date, call_time, tzone(self.fields["timezone"].initial))
            setdate = _mergetime(date, set_time) if set_time else None
            enddate = _mergetime(date, end_time) if end_time else None
        else:
            date = date.replace(tzinfo=tzone(self.fields["timezone"].initial))
            enddate = end_date.replace(tzinfo=tzone(self.fields["timezone"].initial))
            setdate = None

        if date < timezone.now():
            self.add_error(
                "call_date",
                ValidationError(
                    _("Gig call time must be in the future"), code="invalid date"
                ),
            )
        if setdate and setdate < date:
            self.add_error(
                "set_time",
                ValidationError(
                    _("Set time must not be earlier than the call time"),
                    code="invalid set time",
                ),
            )
        if enddate:
            if enddate < date:
                if end_date:
                    self.add_error(
                        "end_date",
                        ValidationError(
                            _("Gig end must not be earlier than the start"),
                            code="invalid end time",
                        ),
                    )
                else:
                    self.add_error(
                        "end_time",
                        ValidationError(
                            _("Gig end must not be earlier than the call time"),
                            code="invalid end time",
                        ),
                    )
            elif setdate and enddate < setdate:
                self.add_error(
                    "end_time",
                    ValidationError(
                        _("Gig end must not be earlier than the set time"),
                        code="invalid end time",
                    ),
                )

        self.cleaned_data["date"] = date
        self.cleaned_data["setdate"] = setdate
        self.cleaned_data["enddate"] = enddate

        super().clean()

    def create_gig_series(self, the_gig, number_to_copy, period):
        """create a series of copies of a gig spaced out over time"""

        if not number_to_copy:
            return

        last_date = the_gig.date
        if period == "day":
            delta = timedelta(days=1)
        elif period == "week":
            delta = timedelta(weeks=1)
        else:
            day_of_month = last_date.day

        set_delta = (the_gig.setdate - the_gig.date) if the_gig.enddate else None
        end_delta = (the_gig.enddate - the_gig.date) if the_gig.enddate else None

        for _ in range(1, number_to_copy):
            if period == "day" or period == "week":
                last_date = last_date + delta
            else:
                yr = last_date.year
                mo = last_date.month + 1
                if mo > 12:
                    mo = 1
                    yr += 1
                # figure out last day of next month
                last_date = last_date.replace(
                    month=mo,
                    day=min(calendar.monthrange(yr, mo)[1], day_of_month),
                    year=yr,
                )

            the_gig.date = last_date

            if set_delta is not None:
                the_gig.setdate += set_delta

            if end_delta is not None:
                the_gig.enddate += end_delta

            the_gig.id = None
            the_gig.pk = None
            the_gig.cal_feed_id = uuid.uuid4()
            the_gig.save()

    def save(self, commit=True):
        """save our date, setdate, and enddate into the instance"""
        self.instance.date = self.cleaned_data["date"]
        self.instance.setdate = self.cleaned_data["setdate"]
        self.instance.enddate = self.cleaned_data["enddate"]
        newgig = super().save(commit)

        if self.cleaned_data["add_series"] == True:
            save_id = self.instance.id
            self.create_gig_series(
                newgig, self.cleaned_data["total_gigs"], self.cleaned_data["repeat"]
            )
            self.instance.id = save_id
        return newgig

    send_update = forms.BooleanField(
        required=False, label=_("Email members about change")
    )
    call_date = forms.Field(required=True, label=_("Date"))
    call_time = forms.Field(required=False, label=_("Call Time"))
    set_time = forms.Field(required=False, label=_("Set Time"))
    end_time = forms.Field(required=False, label=_("End Time"))
    end_date = forms.Field(required=False, label=_("End Date"))
    timezone = forms.Field(required=False, widget=forms.HiddenInput())
    datenotes = forms.Field(required=False, label=_("Date Notes"))

    is_private = forms.BooleanField(
        required=False, label=_("Hide From Public Gig Feed")
    )

    add_series = forms.BooleanField(required=False, label=_("Add A Series Of Copies"))
    total_gigs = forms.IntegerField(
        required=False, label=_("Total Number Of Gigs"), min_value=1, max_value=10
    )
    repeat = forms.ChoiceField(
        required=False,
        label=_("Repeat Every"),
        choices=[
            ("day", _("day")),
            ("week", _("week")),
            ("month", _("month (on same day of the month)")),
        ],
    )

    class Meta:
        model = Gig
        localized_fields = "__all__"

        fields = [
            "title",
            "contact",
            "status",
            "is_private",
            "call_date",
            "call_time",
            "set_time",
            "end_time",
            "end_date",
            "address",
            "dress",
            "paid",
            "leader",
            "postgig",
            "details",
            "setlist",
            "rss_description",
            "invite_occasionals",
            "hide_from_calendar",
            "send_update",
            "add_series",
            "total_gigs",
            "datenotes",
        ]

        widgets = {
            "title": forms.TextInput(attrs={"placeholder": _("required")}),
            "address": forms.TextInput(attrs={"placeholder": _("Cloudcuckooland")}),
            "dress": forms.TextInput(attrs={"placeholder": _("Pants Optional")}),
            "paid": forms.TextInput(attrs={"placeholder": _("As If")}),
            "postgig": forms.TextInput(attrs={"placeholder": _("Hit the streets!")}),
            "details": forms.Textarea(
                attrs={"placeholder": _("who? what? where? when? why?")}
            ),
            "setlist": forms.Textarea(attrs={"placeholder": _("setlist here")}),
        }

        labels = {
            "title": _("Gig Title"),
            "contact": _("Contact"),
            "status": _("Status"),
            "call_date": _("Date"),
            "end_date": _("End Date"),
            "address": _("Address or URL"),
            "dress": _("What to Wear"),
            "paid": _("Pay Deal"),
            "leader": _("Leader"),
            "postgig": _("Post-gig Plans"),
            "details": _("Details"),
            "setlist": _("Setlist"),
            "hide_from_calendar": _("hide from calendar"),
            "invite_occasionals": _("Invite occasional members"),
        }
