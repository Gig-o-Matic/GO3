from django.http import HttpResponse
from .models import Band, Assoc, Section
from member.models import Member
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


@login_required
def set_assoc_color(request, ak, colorindex):
    """ set a default section on an assoc """
    a = Assoc.objects.filter(id=ak)

    # todo make sure this is us, or we're superuser
    if len(a) != 1:
        raise ValueError('altering an assoc that does not exist')
    else:
        a=a[0]

        if request.user != a.member and not request.user.is_superuser:
            raise PermissionError('tying to alter an assoc which is not owned by user {0}'.format(request.user.username))

        a.color = colorindex
        a.save()

    return HttpResponse()


@login_required
def create_assoc(request, bk, mk):
    b = Band.objects.get(id=bk)
    m = Member.objects.get(id=mk)

    # todo make sure this is us, or we're superuser
    if request.user != m and not request.user.is_superuser:
        raise PermissionError('tying to create an assoc which is not owned by user {0}'.format(request.user.username))

    # OK, create the assoc
    a = Assoc.objects.get_or_create(band=b, member=m)

    return HttpResponse()


@login_required
def delete_assoc(request, ak):
    a = Assoc.objects.get(id=ak)

    # todo make sure this is us, or we're superuser
    if request.user != a.member and not request.user.is_superuser:
        raise PermissionError('tying to delete an assoc which is not owned by user {0}'.format(request.user.username))
    
    a.delete()

    return HttpResponse()

