from django.http import HttpResponse
from .models import Member
from django.views import generic

def index(request):
    return HttpResponse("Hello, world. You're at the member index.")

class DetailView(generic.DetailView):
    model = Member
    template_name = 'member/detail.html'
