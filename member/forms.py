import logging
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext as _
from .models import Member, EmailConfirmation


class MemberCreateForm(UserCreationForm):

    class Meta:
        model = Member
        fields = ("username", "nickname")

    def __init__(self, *args, **kw):
        self.invite = kw.pop("invite")
        super().__init__(*args, label_suffix="", **kw)

    def clean(self):
        super().clean()
        if Member.objects.filter(email=self.invite.email).count() > 0:
            logging.error(
                f'Trying to create a user with "{self.invite.email}", but member already exists.  Invite {self.invite.id}.'
            )
            # This appears in a ul.errorlist.nonfield above the rest of the form
            raise ValidationError(
                _(
                    'Member with email "{email}" already exists.  If you believe this to be an error, please contact superuser@gig-o-matic.com.'
                ).format(email=self.invite.email)
            )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.invite.email
        if commit:
            user.save()
        return user


class MemberChangeForm(UserChangeForm):
    class Meta:
        model = Member
        fields = ["email", "username", "nickname", "phone", "statement", "images"]

    def clean_email(self):
        if "email" in self.changed_data:
            # first, see if there's already someone using that email
            try:
                m = Member.objects.get(email=self.cleaned_data["email"])
            except Member.DoesNotExist:
                m = None

            if m is not None:
                self.add_error("email", _("This email address is already in use."))
            else:
                # we can use this email

                # make sure we don't have another confirmation sitting around already
                EmailConfirmation.objects.filter(member=self.instance).delete()

                c = EmailConfirmation(
                    member=self.instance, new_email=self.cleaned_data["email"]
                )
                c.save()

        # no matter what, don't change the member's current email address
        return self.instance.email


class InviteForm(forms.Form):
    emails = forms.CharField(widget=forms.Textarea)


class SignupForm(forms.Form):
    email = forms.EmailField()
