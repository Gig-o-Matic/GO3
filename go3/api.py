from django.http import JsonResponse
from ninja import NinjaAPI, Schema
from ninja.errors import ValidationError
from ninja.security import APIKeyHeader

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
        member = Member.objects.filter(api_key=key).first()
        if member:
            return {"key": key}
        else:
            raise InvalidAPIKeyError



api = NinjaAPI(auth=BandAPIKey())


@api.exception_handler(InvalidAPIKeyError)
def invalid_api_key(request, exc):
    return JsonResponse({"message": "Invalid API key"}, status=401)

@api.exception_handler(MissingAPIKeyError)
def missing_api_key(request, exc):
    return JsonResponse({"message": "Missing API key"}, status=401)

@api.exception_handler(ValidationError)
def invalid_filter(request, exc):
    return JsonResponse({"message": "Invalid filter"}, status=422)


@api.get("/whoami")
def whoami(request):
    return {"key": request.auth.get("key")}


api.add_router("/gigs", gig_router)