import logging
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from .models import Member

class MemberCreateForm(UserCreationForm):

    class Meta:
        model = Member
        fields = ('username', 'nickname')

    def __init__(self, *args, **kw):
        self.invite = kw.pop('invite')
        super().__init__(*args, **kw)

    def clean(self):
        super().clean()
        if Member.objects.filter(email=self.invite.email).count() > 0:
            logging.error(f'Trying to create a user with "{self.invite.email}", but member already exists.  Invite {self.invite.id}.')
            # This appears in a ul.errorlist.nonfield above the rest of the form
            raise ValidationError(f'Member with email "{self.invite.email}" already exists.  If you believe this to be an error, please contact superuser@gig-o-matic.com.')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.invite.email
        if commit:
            user.save()
        return user
