from typing import List, Optional

from django.http import JsonResponse
from ninja import Field, FilterSchema, ModelSchema, Query, Router, Schema

from gig.models import Gig, Plan
from gig.util import GigStatusChoices, PlanStatusChoices
from member.models import Member

class CannotResolveMemberStatus(Exception):
    pass

class CannotResolveGigStatus(Exception):
    pass

router = Router()

class Message(Schema):
    message: str

class GigSchema(ModelSchema):
    id: int
    member_status: str
    band: Optional[str] = None
    contact: Optional[str] = None
    leader: Optional[str] = None
    date: Optional[str] = None
    call_time: Optional[str] = None
    set_time: Optional[str] = None
    end_time: Optional[str] = None
    gig_status: Optional[str] = None

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
    def resolve_member_status(obj, context):
        plans = obj.member_plans
        if plans:
            auth_key = context.get("request").auth.get("key")
            member = Member.objects.filter(api_key=auth_key).first()
            if member:
                plan = plans.filter(assoc__member=member).first()
                if plan:
                    try:
                        return next((str(choice[1]) for choice in PlanStatusChoices.choices if choice[0] == plan.status))
                    except StopIteration:
                        raise CannotResolveMemberStatus
        raise CannotResolveMemberStatus

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
    def resolve_gig_status(obj):
        
        try:
            return next((str(choice[1]) for choice in GigStatusChoices.choices if choice[0] == obj.status))
        except StopIteration:
            raise CannotResolveGigStatus


class GigListResponse(Schema):
    count: int
    gigs: List[GigSchema]


class GigFilterSchema(FilterSchema):
    gig_status: Optional[int] = Field(None, description="Filter by gig status")
    plan_status: Optional[int] = Field(None, description="Filter by plan status")

@router.get("", response={200: GigListResponse, 401: Message})
def list_all_gigs(request, filters: GigFilterSchema = Query(...)):
    """
    Retrieve a list of all gigs.

    This endpoint retrieves a list of all gigs. The list can be filtered by gig status, member status.

    If the API key belongs to a band, the endpoint will return all gigs for that band. If the API key belongs to a member, the endpoint will return all future gigs for that member.

    Key type is determined by the API key used for authentication and displayed for informational purposes.
    """
    api_key = request.auth.get("key")
    member = Member.objects.filter(api_key=api_key).first()
    if not member:
        return JsonResponse({"message": "Unauthorized"}, status=401)
    else:
        # get all gigs for the member
        plans = Plan.objects.filter(assoc__member=member)
        gigs = Gig.objects.none()
        for plan in plans:
            if filters.plan_status in [status[0] for status in PlanStatusChoices.choices]:
                if plan.status != filters.plan_status:
                    continue
                else:
                    gig_qs = Gig.objects.filter(pk=plan.gig_id)
            else:
                gig_qs = Gig.objects.filter(pk=plan.gig_id)

            if filters.gig_status in [status[0] for status in GigStatusChoices.choices]:
                gig_qs = gig_qs.filter(status=filters.gig_status)
            if gig_qs.exists():
                gigs |= gig_qs
    return {"count": gigs.count(), "gigs": gigs if gigs else []}

@router.get("/plan_status_choices", response={200: List[dict]})
def plan_status_choices(request):
    """Retrieve the available plan status choices."""
    return [{"id": status[0], "name": status[1]} for status in PlanStatusChoices.choices]

@router.get("/gig_status_choices", response={200: List[dict]})
def gig_status_choices(request):
    """Retrieve the available gig status choices."""
    return [{"id": status[0], "name": status[1]} for status in GigStatusChoices.choices]

@router.get("/{gig_id}", response={200: GigSchema, 404: Message})
def get_gig(request, gig_id: int):
    """Retrieve a specific gig by its ID if it belongs to the authenticated member plans."""
    api_key = request.auth.get("key")
    member = Member.objects.filter(api_key=api_key).first()

    if member:
        gig = Gig.objects.filter(pk=gig_id).first()
        if gig:
            plan = Plan.objects.filter(gig=gig, assoc__member
            =member).first()
            if plan:
                return gig
    return JsonResponse({"message": "Not found"}, status=404)
