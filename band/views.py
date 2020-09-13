import csv
from django.http import HttpResponse, HttpResponseForbidden
from django.views import generic
from django.views.generic.edit import UpdateView as BaseUpdateView
from django.views.generic.base import TemplateView
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
from .models import Band, Assoc, Section
from .forms import BandForm
from .util import AssocStatusChoices, BandStatusChoices
from member.models import Invite
from member.util import MemberStatusChoices
import json
from django.utils.safestring import SafeString



class BandMemberRequiredMixin(AccessMixin):
    """Verify that the current user is authenticated."""
    def dispatch(self, request, *args, **kwargs):
        band = get_object_or_404(Band, pk=kwargs['pk'])
        is_band_member = Assoc.objects.filter(
            member=request.user, band=band, status=AssocStatusChoices.CONFIRMED).count() == 1
        if not (is_band_member or request.user.is_superuser):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class BandList(LoginRequiredMixin, generic.ListView):
    queryset = Band.objects.filter(status=BandStatusChoices.ACTIVE).order_by('name')
    context_object_name = 'bands'


class DetailView(generic.DetailView):
    model = Band
    # fields = ['name', 'hometown']

    def get_context_data(self, **kwargs):
        the_band = self.object
        the_user = self.request.user

        context = super().get_context_data(**kwargs)

        try:
            assoc = Assoc.objects.get(band=the_band, member=the_user)
        except Assoc.DoesNotExist:
            context['the_user_is_associated'] = False
        else:
            context['the_user_is_associated'] = True
            context['the_user_is_band_admin'] = assoc.is_admin

            context['the_pending_members'] = Assoc.objects.filter(band=the_band, status=AssocStatusChoices.PENDING)
            context['the_invited_members'] = Invite.objects.filter(band=the_band)
        return context

    def get_success_url(self):
        return reverse('member-detail', kwargs={'pk': self.object.id})


class UpdateView(LoginRequiredMixin, BaseUpdateView):
    model = Band
    form_class = BandForm
    def get_success_url(self):
        return reverse('band-detail', kwargs={'pk': self.object.id})


class AllMembersView(LoginRequiredMixin, TemplateView):
    template_name='band/band_all_members.html'
    def get_context_data(self, **kwargs):
        the_band = Band.objects.get(id=self.kwargs['pk'])
        context = super().get_context_data(**kwargs)
        context['member_assocs'] = the_band.confirmed_assocs
        return context

class SectionMembersView(LoginRequiredMixin, TemplateView):
    template_name='band/band_section_members.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        b = Band.objects.get(id=self.kwargs['pk'])
        # prefetching seems to his the database more
        # b = Band.objects.prefetch_related('assocs').filter(id=self.kwargs['pk'])

        # make sure I'm in the band or am superuser
        u = self.request.user
        if  u.is_superuser is False and not b.has_member(u):
            raise ValueError('user {0} accessing section members for non-member band'.format(u.email))

        if self.kwargs['sk']:
            s = Section.objects.filter(id=self.kwargs['sk'])
            if len(s) != 1:
                raise ValueError('getting info on a section that does not exist')

            s = s[0]

            if s.band != b:
                raise ValueError('accessing a section by wrong band')
        else:
            s = None

        context['has_sections'] = True if len(b.sections.all()) > 0 else False
        context['the_section'] = s
        context['the_assocs'] = b.assocs.filter(status=AssocStatusChoices.CONFIRMED, default_section=s, 
                                                member__status=MemberStatusChoices.ACTIVE).all()
        return context

class TrashcanView(LoginRequiredMixin, BandMemberRequiredMixin, TemplateView):
    template_name='band/band_gig_trashcan.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['band'] = get_object_or_404(Band, pk=kwargs['pk'])
        return context

class ArchiveView(LoginRequiredMixin, BandMemberRequiredMixin, TemplateView):
    template_name='band/band_gig_archive.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['band'] = get_object_or_404(Band, pk=kwargs['pk'])
        return context

class SectionSetupView(LoginRequiredMixin, BandMemberRequiredMixin, TemplateView):
    template_name='band/band_section_setup.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        band = get_object_or_404(Band, pk=kwargs['pk'])
        context['band'] = band

        # set up the list of current sections
        sections = band.sections
        thelist = []
        for s in sections.all():
            if not s.is_default:
                thelist.append([s.name, s.id, s.name])
        context['the_sections'] = SafeString(json.dumps(thelist))

        return context

@login_required
def member_spreadsheet(request, pk):
    band = get_object_or_404(Band, pk=pk)
    if not (band.is_admin(request.user) or request.user.is_superuser):
        raise PermissionDenied

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{band.shortname or band.name}.csv"'
    writer = csv.writer(response)
    writer.writerow(['name', 'nickname', 'email', 'phone', 'section'])
    for assoc in band.confirmed_assocs:
        member = assoc.member
        writer.writerow([member.username, member.nickname, member.email, member.phone, assoc.section.name])

    return response


@login_required
def member_emails(request, pk):
    band = get_object_or_404(Band, pk=pk)
    if not (band.is_admin(request.user) or request.user.is_superuser):
        raise PermissionDenied

    emails = ', '.join(a.member.email for a in band.confirmed_assocs)
    return render(request, 'band/member_emails.html', context={'band': band, 'emails': emails})
