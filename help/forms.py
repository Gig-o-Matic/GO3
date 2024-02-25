from django import forms
from django.utils.translation import gettext_lazy as _


class BandRequestForm(forms.Form):
    email = forms.EmailField(label=_("Your email"))
    name = forms.CharField(label=_("Your name"))
    message = forms.CharField(
        label=_("Tell us a little about the band"), widget=forms.Textarea
    )
