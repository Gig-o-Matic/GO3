from django import forms
from .models import Band

class BandForm(forms.ModelForm):
    def __init__(self, **kwargs):
        super().__init__(
            label_suffix='',
            **kwargs
        )

    class Meta:
        model = Band
        fields = ['name', 'shortname', 'hometown', 'description', 'member_links', 'website',
            'new_member_message', 'thumbnail_img', 'images', 'timezone',
            'anyone_can_create_gigs', 'anyone_can_manage_gigs', 'share_gigs',
            'send_updates_by_default', 'rss_feed', 'simple_planning', 'plan_feedback']

        widgets = {
            'images': forms.Textarea(attrs={'placeholder': 'put urls to images on their own lines...'}),
        }
