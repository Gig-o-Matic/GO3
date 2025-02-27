from django.conf import settings
from django.http import JsonResponse
from ninja import Router
from ninja.security import APIKeyHeader

from band.models import Band
from gig.models import Gig


class GigAPIKey(APIKeyHeader):
    param_name = "X-API-Key"

    def authenticate(self, request, key):
        """
        This method is called to authenticate the request.
        Should return None if authentication fails.
        Should return any truthy value (for example, the api key string)
        if authentication is successful.

        :param request: Django request
        :param key: value of the header
        :return: str or None
        """
        # if settings.DEBUG:
        #     return key
        band = Band.objects.filter(api_key=key).first()
        if band:
            return key
        return None

router = Router()

@router.get("/all", auth=GigAPIKey())
def list_all_gigs(request):
    api_key = request.auth
    band = Band.objects.get(api_key=api_key)
    gigs = band.gigs.all()
    return JsonResponse({"gigs": list(gigs.values()), "count": gigs.count()})