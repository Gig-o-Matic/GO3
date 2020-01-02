from django.http import HttpResponse
from .models import Assoc, Section
from django.contrib.auth.decorators import login_required

@login_required
def set_assoc_tfparam(request, ak, param, truefalse):
    """ set a true/false parameter on an assoc """
    a = Assoc.objects.filter(id=ak)

    if len(a) != 1:
        raise ValueError('altering an assoc that does not exist')
    else:
        a=a[0]

        if request.user != a.member and not request.user.is_superuser:
            raise PermissionError('tying to alter an assoc which is not owned by user {0}'.format(request.user.username))

        if hasattr(a, param):
            setattr(a, param, True if truefalse=='true' else False)
            a.save()
        else:
            raise ValueError('trying to set an assoc parameter that does not exist: {0}'.format(param))
    return HttpResponse()


@login_required
def set_assoc_section(request, ak, sk):
    """ set a default section on an assoc """
    a = Assoc.objects.filter(id=ak)

    # todo make sure this is us, or we're superuser
    if len(a) != 1:
        raise ValueError('altering an assoc that does not exist')
    else:
        a=a[0]

        if request.user != a.member and not request.user.is_superuser:
            raise PermissionError('tying to alter an assoc which is not owned by user {0}'.format(request.user.username))

        if sk == 0:
            s = None
        else:
            s=Section.objects.filter(id=sk)
            if len(s) != 1:
                raise ValueError('setting a section that does not exist')
            s=s[0]
            if s.band != a.band:
                raise ValueError('setting a section that is not part of the band')

        a.default_section=s
        a.save()
    return HttpResponse()