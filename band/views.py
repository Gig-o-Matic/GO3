from django.http import HttpResponse
from .models import Band
from django.views import generic

def index(request):
    return HttpResponse("Hello, world. You're at the band index.")

class DetailView(generic.DetailView):
    model = Band
    fields = ['name', 'hometown']
    def get_success_url(self):
        return reverse('member-detail', kwargs={'pk': self.object.id})

