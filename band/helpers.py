from django.http import HttpResponse
from .models import Assoc

def set_param(request, ak, param, truefalse):
    a = Assoc.objects.filter(id=ak)

    # todo make sure this is us, or we're superuser
    if len(a) != 1:
        raise ValueError('altering an assoc that does not exist')
    else:
        a=a[0]
        if hasattr(a, param):
            setattr(a, param, True if truefalse=='true' else False)
            a.save()
        else:
            raise ValueError('trying to set a parameter that does not exist: {0}'.format(param))
    return HttpResponse()