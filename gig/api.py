from typing import List, Optional

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_list_or_404, get_object_or_404
from ninja import Field, FilterSchema, ModelSchema, Query, Router, Schema
from ninja.responses import codes_4xx

from band.models import Band
from gig.models import Gig
from gig.util import GigStatusChoices, PlanStatusChoices
from member.models import Member

router = Router()

class Message(Schema):
    message: str

class GigSchema(ModelSchema):
    id: int 
    band: Optional[str] = None
    contact: Optional[str] = None
    leader: Optional[str] = None
    date: Optional[str] = None
    call_time: Optional[str] = None
    set_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None

    class Meta:
        model = Gig
        fields = [
            "datenotes",
            "title",
            "details",
            "setlist",
            "dress",
            "paid",
            "postgig",
            "is_full_day",
            "address",
            "is_archived",
            "is_private",
        ]

    @staticmethod
    def resolve_band(obj):
        return obj.band.name
    
    @staticmethod
    def resolve_contact(obj):
        return obj.contact.member_name
    
    @staticmethod
    def resolve_leader(obj):
        return obj.leader.name if obj.leader else obj.leader_text
    
    @staticmethod
    def resolve_date(obj):
        return obj.date.strftime("%Y-%m-%d") if obj.date else obj.setdate.strftime("%Y-%m-%d")
    
    @staticmethod
    def resolve_call_time(obj):
        return obj.date.strftime("%H:%M") if obj.date else obj.setdate.strftime("%H:%M")
    
    @staticmethod
    def resolve_set_time(obj):
        return obj.setdate.strftime("%H:%M") if obj.setdate else ""
    
    @staticmethod
    def resolve_end_time(obj):
        return obj.enddate.strftime("%H:%M") if obj.enddate else ""

    @staticmethod
    def resolve_status(obj):
        return next((str(choice[1]) for choice in GigStatusChoices.choices if choice[0] == obj.status), "Unconfirmed")


class GigListResponse(Schema):
    key_type: str
    count: int
    gigs: List[GigSchema]


class GigFilterSchema(FilterSchema):
    gig_status: Optional[int] = Field(None, description="Filter by gig status")
    member_status: Optional[int] = Field(None, description="Filter by member status")

@router.get("", response={200: GigListResponse, 401: Message})
def list_all_gigs(request, filters: GigFilterSchema = Query(...)):
    """
    Retrieve a list of all gigs.

    This endpoint retrieves a list of all gigs. The list can be filtered by gig status, member status, and plan.

    If the API key belongs to a band, the endpoint will return all gigs for that band. If the API key belongs to a member, the endpoint will return all future gigs for that member.

    Key type is determined by the API key used for authentication and displayed for informational purposes.
    """
    api_key = request.auth.get("key")
    band = Band.objects.filter(Q(read_api_key=api_key) | Q(write_api_key=api_key)).first()
    member = Member.objects.filter(api_key=api_key).first()
    if not band and not member:
        return JsonResponse({"message": "Unauthorized"}, status=401)


    gigs = []
    if band:
        # get all gigs for the band
        if filters.gig_status:
            gigs = band.gigs.filter(status=filters.gig_status)
        else:
            gigs = band.gigs.all()
    else:
        # get all future gigs for the member
        plans = member.future_plans
        gigs = Gig.objects.none()
        for plan in plans:
            if filters.member_status:
                if plan.status != filters.member_status:
                    gig_qs = Gig.objects.none()
                else:
                    gig_qs = Gig.objects.filter(pk=plan.gig_id)
            else:
                gig_qs = Gig.objects.filter(pk=plan.gig_id)

            if filters.gig_status:
                gig_qs = gig_qs.filter(status=filters.gig_status)
            if gig_qs:
                gigs |= gig_qs
    return {"key_type": request.auth.get("key_type"), "count": gigs.count(), "gigs": gigs if gigs else []}

@router.get("/member_status_choices", response={200: List[dict]})
def member_status_choices(request):
    """Retrieve the available member status choices."""
    return [{"id": status[0], "name": status[1]} for status in PlanStatusChoices.choices]

@router.get("/gig_status_choices", response={200: List[dict]})
def gig_status_choices(request):
    """Retrieve the available gig status choices."""
    return [{"id": status[0], "name": status[1]} for status in GigStatusChoices.choices]

@router.get("/{gig_id}", response={200: GigSchema, 404: Message})
def get_gig(request, gig_id: int):
    """Retrieve a specific gig by its ID if it belongs to the authenticated band or member future plans."""
    api_key = request.auth.get("key")
    band = Band.objects.filter(Q(read_api_key=api_key) | Q(write_api_key=api_key)).first()
    member = Member.objects.filter(api_key=api_key).first()

    if band:
        gig = band.gigs.filter(pk=gig_id).first()
        if gig:
            return gig
    elif member:
        plan = member.future_plans.filter(gig_id=gig_id).first()
        if plan:
            return plan.gig
    return JsonResponse({"message": "Not found"}, status=404)
