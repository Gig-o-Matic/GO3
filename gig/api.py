from django.http import JsonResponse
from ninja import Router

from band.models import Band

router = Router()

@router.get("/all")
def list_all_gigs(request):
    api_key = request.auth
    band = Band.objects.get(api_key=api_key)
    gigs = band.gigs.all()
    return JsonResponse({"gigs": list(gigs.values()), "count": gigs.count()})