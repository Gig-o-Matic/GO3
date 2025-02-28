from django.conf import settings
from django.http import JsonResponse
from ninja import NinjaAPI, Schema
from ninja.security import APIKeyHeader

from band.models import Band
from gig.api import router as gig_router
from member.models import Member


class Message(Schema):
    message: str

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
        member = Member.objects.filter(api_key=key).first()
        if band or member:
            return key
        return None
    

api = NinjaAPI(auth=BandAPIKey())

@api.get("/key_type", response={200: Message, 401: Message})
def key_type(request):
    
    """
    Retrieve the type of API key used for authentication.
    """
    api_key = request.auth
    band = Band.objects.filter(read_api_key=api_key).first() or Band.objects.filter(write_api_key=api_key).first()
    member = Member.objects.filter(api_key=api_key).first()
    if not band and not member:
        return JsonResponse({"message": "Unauthorized"}, status=401)
    
    if band:
        read_key = band.read_api_key
        write_key = band.write_api_key
        key_type = f"band ({'read' if read_key == api_key else 'write'})"
    else:
        key_type = "member"
    return JsonResponse({"key_type": key_type})

api.add_router("/gigs", gig_router)