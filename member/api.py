from typing import Optional

from django.http import JsonResponse
from ninja import Router, Schema

from member.models import Member

router = Router()


class Message(Schema):
    message: str


class MemberCreateSchema(Schema):
    """
    Schema for creating a new member.
    """
    email: str
    username: str
    password: str
    nickname: Optional[str] = None
    phone: Optional[str] = None


class MemberResponseSchema(Schema):
    """
    Schema for member response.
    """
    id: int
    email: str
    username: str
    nickname: Optional[str] = None
    phone: Optional[str] = None


@router.post("", response={201: MemberResponseSchema, 400: Message, 409: Message})
def create_member(request, payload: MemberCreateSchema):
    """
    Create a new member.

    This endpoint creates a new member with the provided email, username, and password.
    Email must be unique. Nickname and phone are optional.

    Returns 201 with the created member data on success.
    Returns 400 if validation fails.
    Returns 409 if a member with the email already exists.
    """
    # Check if member with this email already exists
    if Member.objects.filter(email=payload.email.lower()).exists():
        return 409, {"message": f"Member with email '{payload.email}' already exists"}
    
    try:
        # Create the member using the manager's create_user method
        member = Member.objects.create_user(
            email=payload.email,
            password=payload.password,
            username=payload.username,
            nickname=payload.nickname,
            phone=payload.phone
        )
        
        return 201, {
            "id": member.id,
            "email": member.email,
            "username": member.username,
            "nickname": member.nickname,
            "phone": member.phone
        }
    except Exception as e:
        return 400, {"message": f"Failed to create member: {str(e)}"}
