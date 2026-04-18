from typing import List
from ninja import Router, Schema
from ninja.throttling import AuthRateThrottle
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from member.helpers import send_band_invites
from member.models import Member
from band.models import Band, Assoc


router = Router()


class InviteRequest(Schema):
    emails: List[str]


class InviteResponse(Schema):
    invited: List[str]
    in_band: List[str]
    invalid: List[str]


class Message(Schema):
    message: str


class OccasionalResponse(Schema):
    member_id: int
    band_id: int
    is_occasional: bool


@router.post("/{band_id}/invites", response={200: InviteResponse, 401: Message, 404: Message, 403: Message}, throttle=[AuthRateThrottle('20/h')])
def invite_to_band(request, band_id: int, payload: InviteRequest):
    """
    Send invitations to multiple members for a specific band.
    
    Requires the authenticated user to be an admin of the band.
    
    Accepts a list of email addresses and:
    - Creates invitations for new members
    - Updates status for existing non-confirmed members
    - Returns lists of invited, already in band, and invalid emails
    
    Returns:
    - 200: Invitation results
    - 401: Unauthorized (invalid API key)
    - 404: Band not found
    - 403: User is not a band admin
    """
    # Get the authenticated member from the API key
    api_key = request.auth.get("key")
    member = Member.objects.get(api_key=api_key)
    
    band = get_object_or_404(Band, pk=band_id)
    
    # Check if user is admin of the band
    if not band.is_admin(member):
        return JsonResponse({"message": "You do not have permission to invite members to this band"}, status=403)
    
    # Get user's language preference for the invitations
    language = member.preferences.language if hasattr(member, 'preferences') else 'en-US'
    
    result = send_band_invites(band, payload.emails, language)
    
    return {
        'invited': result['invited'],
        'in_band': result['in_band'],
        'invalid': result['invalid']
    }


@router.patch("/{band_id}/members/{member_id}/occasional", response={200: OccasionalResponse, 401: Message, 404: Message, 403: Message}, throttle=[AuthRateThrottle('20/h')])
def toggle_occasional_member(request, band_id: int, member_id: int):
    """
    Toggle the occasional status for a member in a band.
    
    Requires the authenticated user to be an admin of the band.
    
    Returns:
    - 200: Updated occasional status
    - 401: Unauthorized (invalid API key)
    - 404: Band or member not found
    - 403: User is not a band admin
    """
    # Get the authenticated member from the API key
    api_key = request.auth.get("key")
    member = Member.objects.get(api_key=api_key)
    
    band = get_object_or_404(Band, pk=band_id)
    
    # Check if user is admin of the band
    if not band.is_admin(member):
        return JsonResponse({"message": "You do not have permission to modify members in this band"}, status=403)
    
    # Get the association between the member and band
    assoc = get_object_or_404(Assoc, band=band, member_id=member_id)
    
    # Toggle the is_occasional field
    assoc.is_occasional = not assoc.is_occasional
    assoc.save()
    
    return {
        'member_id': assoc.member.id,
        'band_id': assoc.band.id,
        'is_occasional': assoc.is_occasional
    }

