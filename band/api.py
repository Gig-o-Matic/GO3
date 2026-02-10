from typing import List
from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from member.helpers import send_band_invites
from member.models import Member
from band.models import Band


router = Router()


class InviteRequest(Schema):
    emails: List[str]


class InviteResponse(Schema):
    invited: List[str]
    in_band: List[str]
    invalid: List[str]


class Message(Schema):
    message: str


@router.post("/{band_id}/invites", response={200: InviteResponse, 401: Message, 404: Message, 403: Message})
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
    member = Member.objects.filter(api_key=api_key).first()
    
    if not member:
        return JsonResponse({"message": "Unauthorized"}, status=401)
    
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

