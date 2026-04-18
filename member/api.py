from ninja import Router, Schema
from ninja.throttling import AuthRateThrottle
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db.models import Q

from member.models import Member
from band.models import Band
from band.util import AssocStatusChoices


router = Router()


class Message(Schema):
    message: str


class MemberQueryResponse(Schema):
    member_id: int
    email: str
    username: str


@router.get("/query", response={200: MemberQueryResponse, 401: Message, 404: Message, 403: Message}, throttle=[AuthRateThrottle('20/h')])
def query_member_by_email(request, email: str):
    """
    Query for a member by email address.
    
    Requires the authenticated user to be an admin in at least one band,
    and the queried member must be in the same band(s).
    
    Query Parameters:
    - email: The email address to search for
    
    Returns:
    - 200: Member ID, email, username
    - 401: Unauthorized (invalid API key)
    - 404: Member not found
    - 403: User is not a band admin or member is not in same band
    """
    # Get the authenticated member from the API key
    api_key = request.auth.get("key")
    admin_member = Member.objects.get(api_key=api_key)
    
    # Find the target member by email
    target_member = Member.objects.filter(email__iexact=email).first()
    if not target_member:
        return JsonResponse({"message": "Member not found"}, status=404)
    
    # Get bands where the authenticated user is an admin
    admin_bands = Band.objects.filter(
        assocs__member=admin_member,
        assocs__status=AssocStatusChoices.CONFIRMED,
        assocs__is_admin=True
    ).values_list('id', flat=True)
    
    if not admin_bands.exists():
        return JsonResponse({"message": "You do not have admin access to any bands"}, status=403)
    
    # Check if target member is in any of the same bands where user is admin
    is_in_same_band = Band.objects.filter(
        id__in=admin_bands,
        assocs__member=target_member,
        assocs__status=AssocStatusChoices.CONFIRMED
    ).exists()
    
    if not is_in_same_band:
        return JsonResponse({"message": "Member is not in any of your bands"}, status=403)
    
    return {
        'member_id': target_member.id,
        'email': target_member.email,
        'username': target_member.username
    }
