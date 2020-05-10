from django.shortcuts import render
from django.views.generic.edit import FormView
from django.contrib.auth.decorators import login_required
from .forms import BandRequestForm
from lib import email

@login_required
def help(request):
    return render(request, 'help/help.html')

@login_required
def privacy(request):
    return render(request, 'help/privacy.html')

def whatis(request):
    return render(request, 'help/whatis.html')

class BandRequestView(FormView):
    template_name = 'help/band_request.html'
    form_class = BandRequestForm

    def form_valid(self, form):
        recipient = email.EmailRecipient(email='gigomatic.superuser@gmail.com')
        message = email.prepare_email(recipient, 'email/band_request.md', form.cleaned_data)
        email.send_messages_async([message])
        return render(self.request, 'help/confirm_band_request.html')
