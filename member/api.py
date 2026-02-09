from ninja import Router, Schema
from member.helpers import create_signup_invite


router = Router()


class SignupRequest(Schema):
    email: str


class SignupResponse(Schema):
    success: bool
    message: str
    email: str


@router.post("/signup", response={200: SignupResponse, 422: dict})
def signup(request, payload: SignupRequest):
    """
    Create a signup invitation for a new member.
    
    Accepts an email address and creates an invitation that will be sent to that email.
    The recipient can then activate their account by following the link in the email.
    
    Returns 200 with details if successful or if the account already exists.
    Returns 422 if the email format is invalid.
    """
    result = create_signup_invite(payload.email, request)
    
    return {
        'success': result['success'],
        'message': str(result['message']),
        'email': result['email']
    }
