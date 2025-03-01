from typing import Optional

from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from ninja import NinjaAPI, Schema
from ninja.security import APIKeyHeader

from band.models import Band
from gig.api import router as gig_router
from member.models import Member


class Message(Schema):
    message: str


class InvalidAPIKeyError(Exception):
    pass

class MissingAPIKeyError(Exception):
    pass

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
        :return: 
        """
        if not key:
            raise MissingAPIKeyError
        band = Band.objects.filter(Q(read_api_key=key) | Q(write_api_key=key)).first()
        member = Member.objects.filter(api_key=key).first()
        if band:
            read_key = band.read_api_key
            key_type = f"band ({'read' if read_key == key else 'write'})"
        elif member:
            key_type = "member"
        else:
            raise InvalidAPIKeyError
        return {"key": key, "key_type": key_type}
    



api = NinjaAPI(auth=BandAPIKey())


@api.exception_handler(InvalidAPIKeyError)
def invalid_api_key(request, exc):
    return JsonResponse({"message": "Invalid API key"}, status=401)

@api.exception_handler(MissingAPIKeyError)
def missing_api_key(request, exc):
    return JsonResponse({"message": "Missing API key"}, status=401)


class KeyTypeResponse(Schema):
    key_type: str
    member_name: Optional[str] = "Not a member"
    bands: str
    
@api.get("/key_type", response={200: KeyTypeResponse, 401: Message})
def key_type(request):
    
    """
    Retrieve the type of API key used for authentication.
    """
    api_key = request.auth.get("key")
    band = Band.objects.filter(Q(read_api_key=api_key) | Q(write_api_key=api_key)).first()
    member = Member.objects.filter(api_key=api_key).first()
    bands = band.name if band else None
    if member:
        bands = ", ".join([assoc.band.name for assoc in member.assocs.all()])
        member_name = member.display_name
        return {"key_type": request.auth.get("key_type"), "member_name": member_name, "bands": bands}
    return {"key_type": request.auth.get("key_type"), "bands": bands}

api.add_router("/gigs", gig_router)