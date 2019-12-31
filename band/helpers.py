from django.http import HttpResponse
from .models import Assoc

def set_occasional(request, ak, truefalse):
    a = Assoc.objects.filter(id=ak)
    if len(a) != 1:
        raise ValueError('altering an assoc that does not exist')
    else:
        a=a[0]
        a.is_occasional = True if truefalse=='true' else False
        a.save()
    return HttpResponse()