from django.http import HttpResponse
from .models import Band
from django.views import generic

def index(request):
    return HttpResponse("Hello, world. You're at the band index.")

class DetailView(generic.DetailView):
    model = Band
    template_name = 'band/detail.html'

