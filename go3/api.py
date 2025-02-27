from django.conf import settings
from ninja import NinjaAPI
from ninja.security import APIKeyHeader

from band.models import Band
from gig.api import router as gig_router


class BandAPIKey(APIKeyHeader):
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
        if settings.DEBUG:
            return key
        band = Band.objects.filter(api_key=key).first()
        if band:
            return key
        return None
    

api = NinjaAPI(auth=BandAPIKey())

api.add_router("/gigs", gig_router)