import graphene
from graphene_django import DjangoObjectType

from gig.models import Gig
from band.models import Band, Assoc
from member.models import Member
from graphql import GraphQLError\



class GigType(DjangoObjectType):
    class Meta:
        model = Gig
        fields = ("title", "date", "status")


class BandType(DjangoObjectType):
    class Meta:
        model = Band
        fields = ("name", "hometown", "creation_date")


class AssocType(DjangoObjectType):
    class Meta:
        model = Assoc
        fields = ("band", "member", "status")


class MemberType(DjangoObjectType):
    class Meta:
        model = Member
        fields = ("email", "username")


class Query(graphene.ObjectType):
    all_gigs = graphene.List(GigType)
    all_bands = graphene.List(AssocType)
    band_by_name = graphene.Field(
        BandType, name=graphene.String(required=True))
    all_members = graphene.List(MemberType)
    member_by_email = graphene.Field(
        MemberType, email=graphene.String(required=True))

    def resolve_all_gigs(self, info):
        user = info.context.user

        if not user.is_authenticated:
            return Gig.objects.none()
        elif user.is_superuser:
            return Gig.objects.all()
        else:
            assocs = Assoc.objects.filter(member=user)
            band_ids = assocs.values_list('band', flat=True)
            gigs = Gig.objects.filter(band__in=band_ids)
            return gigs

    def resolve_all_bands(self, info):
        user = info.context.user
        assocs = Assoc.objects.filter(member=user)

        if not info.context.user.is_authenticated:
            return Assoc.objects.none()
        elif info.context.user.is_superuser:
            return Assoc.objects.all()
        else:
            return assocs

    ''' superuser only '''

    def resolve_band_by_name(self, info, name):
        try:
            if info.context.user.is_superuser:
                return Band.objects.get(name=name)
            else:
                raise GraphQLError(
                    'User is not authorized for this operation.')
        except Band.DoesNotExist:
            # return None
            raise GraphQLError(
                "Requested band '" + name + "' does not exist.")

    def resolve_all_members(self, info):
        if info.context.user.is_superuser:
            return Member.objects.all()
        else:
            raise GraphQLError(
                'User is not authorized for this operation.')

    def resolve_member_by_email(self, info, email):
        try:
            if info.context.user.is_superuser:
                return Member.objects.get(email=email)
            else:
                raise GraphQLError(
                    'User is not authorized for this operation.')
        except Member.DoesNotExist:
            raise GraphQLError(
                "Requested member '" + email + "' does not exist.")


schema = graphene.Schema(query=Query)
