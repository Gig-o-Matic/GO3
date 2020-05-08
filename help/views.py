from django.shortcuts import render
from django.views.generic.edit import FormView
from .forms import BandRequestForm
from lib import email

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
