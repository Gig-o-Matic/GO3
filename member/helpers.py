from django.http import HttpResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required

@login_required
def motd_seen(request, pk):
    """ note that we've seen the motd """
    if request.user.id != pk:
        raise PermissionError('trying to mark MOTD seen for another user')

    request.user.seen_motd_time = timezone.now()
    request.user.save()

    return HttpResponse()
