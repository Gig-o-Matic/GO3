import zoneinfo

from django.utils import timezone

class UserTimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user and not request.user.is_anonymous and request.user.preferences.current_timezone:
            timezone.activate(request.user.preferences.current_timezone)
        else:
            timezone.deactivate()
        return self.get_response(request)