import graphene
from graphene_django import DjangoObjectType

from band.models import *
from member.models import *


class BandType(DjangoObjectType):
    class Meta:
        model = Band
        fields = ("name", "hometown", "creation_date", "last_activity")


class MemberType(DjangoObjectType):
    class Meta:
        model = Member
        fields = ("email", "username")


class Query(graphene.ObjectType):
    all_bands = graphene.List(BandType)
    band_by_name = graphene.Field(
        BandType, name=graphene.String(required=True))
    all_members = graphene.List(MemberType)
    member_by_email = graphene.Field(
        MemberType, email=graphene.String(required=True))

    def resolve_all_bands(self, root):
        return Band.objects.all()

    def resolve_band_by_name(self, root, name):
        try:
            return Band.objects.get(name=name)
        except Band.DoesNotExist:
            return None

    def resolve_all_members(self, root):
        return Member.objects.all()

    def resolve_member_by_email(self, root, email):
        try:
            return Member.objects.get(email=email)
        except Member.DoesNotExist:
            return None


schema = graphene.Schema(query=Query)
