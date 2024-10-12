import csv
from django.http import HttpResponse, HttpResponseForbidden
from django.views import generic
from django.views.generic.edit import UpdateView as BaseUpdateView
from django.views.generic.base import TemplateView
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.db.models.functions import Lower
from django.shortcuts import redirect
from .models import Band, Assoc, Section
from .forms import BandForm
from .util import AssocStatusChoices, _get_active_bands
from member.models import Invite
from member.util import MemberStatusChoices
from member.helpers import has_manage_band_permission
from gig.models import Gig
from stats.helpers import get_band_stats, get_gigs_over_time_stats
from stats.util import dateconverter
import json
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _
from pytz import timezone
from babel.dates import format_date
from go3.settings import URL_BASE

class BandMemberRequiredMixin(UserPassesTestMixin):
    """Verify that the current user is authenticated and is a member of this band (or is the superuser)."""

    def test_func(self):
        # can only edit the band if you're logged in and an admin or superuser
        band = get_object_or_404(Band, id=self.kwargs['pk'])
        return self.request.user and (
            self.request.user.is_superuser or
            band.has_member(self.request.user)
        )

class BandList(LoginRequiredMixin, generic.ListView):
    def get_queryset(self):
        pk_list = [obj.pk for obj in _get_active_bands()]
        return Band.objects.filter(pk__in=pk_list).order_by('name')
    
    context_object_name = 'bands'


class DetailView(LoginRequiredMixin, UserPassesTestMixin, generic.DetailView):
    model = Band

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        # if we're not active in the band, deny entry!
        assoc = Assoc.objects.filter(band=self.kwargs['pk'], member=self.request.user).first()
        return assoc and assoc.status==AssocStatusChoices.CONFIRMED
                
    def get_context_data(self, **kwargs):
        the_band = self.object
        the_user = self.request.user

        context = super().get_context_data(**kwargs)

        context['url_base'] = URL_BASE

        assoc = None if the_user.is_superuser else Assoc.objects.get(band=the_band, member=the_user)
            
        context['the_user_is_band_admin'] = the_user.is_superuser or (assoc and assoc.is_admin)

        context['the_pending_members'] = Assoc.objects.filter(band=the_band, status=AssocStatusChoices.PENDING)
        context['the_invited_members'] = Invite.objects.filter(band=the_band)

        if the_band.member_links:
            links = []
            linklist = the_band.member_links.split('\n')
            for l in linklist:
                parts = l.strip().split(':')
                if len(parts) == 2:
                    links.append([l,l])
                else:
                    links.append([parts[0],':'.join(parts[1:])])
            context['the_member_links'] = links

        if the_band.images:
            context['the_images'] = [l.strip() for l in the_band.images.split('\n')]

        return context

    # todo - we don't need this?
    # def get_success_url(self):
    #     return reverse('member-detail', kwargs={'pk': self.object.id})


class PublicDetailView(TemplateView):
    template_name = 'band/band_public.html'

    def get_context_data(self, **kwargs):
        the_band = get_object_or_404(Band, condensed_name=self.kwargs['name'])
        
        context = super().get_context_data(**kwargs)

        context['band'] = the_band
        context['url_base'] = URL_BASE            
        context['the_user_is_associated'] = False

        if the_band.images:
            context['the_images'] = [l.strip() for l in the_band.images.split('\n')]

        return context

class UpdateView(LoginRequiredMixin, UserPassesTestMixin, BaseUpdateView):
    model = Band
    form_class = BandForm

    def test_func(self):
        # can only edit the band if you're logged in and an admin or superuser
        band = get_object_or_404(Band, id=self.kwargs['pk'])
        return has_manage_band_permission(self.request.user, band)

    def get_success_url(self):
        return reverse('band-detail', kwargs={'pk': self.object.id})


class AllMembersView(LoginRequiredMixin, BandMemberRequiredMixin, TemplateView):
    template_name = 'band/band_all_members.html'

    def get_context_data(self, **kwargs):
        the_band = Band.objects.get(id=self.kwargs['pk'])
        context = super().get_context_data(**kwargs)
        context['member_assocs'] = the_band.confirmed_assocs
        return context


class BandStatsView(LoginRequiredMixin, BandMemberRequiredMixin, TemplateView):
    template_name = 'band/band_stats.html'

    def get_context_data(self, **kwargs):
        the_band = Band.objects.get(id=self.kwargs['pk'])
        context = super().get_context_data(**kwargs)
        context['the_stats'] = get_band_stats(the_band)

        # get the gigs over time data            
        context['gigs_over_time_data'] = json.dumps(get_gigs_over_time_stats(the_band), default=dateconverter)

        if the_band.gigs.count():
            context['last_gig_created'] = the_band.gigs.latest('created_date').created_date
        else:
            context['last_gig_created'] = _('not ever!')

        return context


class SectionMembersView(LoginRequiredMixin, BandMemberRequiredMixin, TemplateView):
    template_name = 'band/band_section_members.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        b = Band.objects.get(id=self.kwargs['pk'])
        # prefetching seems to his the database more
        # b = Band.objects.prefetch_related('assocs').filter(id=self.kwargs['pk'])

        # make sure I'm in the band or am superuser
        u = self.request.user
        if u.is_superuser is False and not b.has_member(u):
            raise ValueError(
                'user {0} accessing section members for non-member band'.format(u.email))

        if self.kwargs['sk']:
            s = Section.objects.filter(id=self.kwargs['sk'])
            if len(s) != 1:
                raise ValueError(
                    'getting info on a section that does not exist')

            s = s[0]

            if s.band != b:
                raise ValueError('accessing a section by wrong band')
        else:
            s = None

        context['has_sections'] = True if len(b.sections.all()) > 0 else False
        context['the_section'] = s
        context['the_assocs'] = b.assocs.filter(status=AssocStatusChoices.CONFIRMED, default_section=s,
                                                member__status=MemberStatusChoices.ACTIVE).order_by(Lower('member__display_name'))
        return context


class TrashcanView(LoginRequiredMixin, BandMemberRequiredMixin, TemplateView):
    template_name = 'band/band_gig_trashcan.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['band'] = get_object_or_404(Band, pk=kwargs['pk'])
        return context


class ArchiveView(LoginRequiredMixin, BandMemberRequiredMixin, TemplateView):
    template_name = 'band/band_gig_archive.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['band'] = get_object_or_404(Band, pk=kwargs['pk'])
        return context


class SectionSetupView(LoginRequiredMixin, BandMemberRequiredMixin, TemplateView):
    template_name = 'band/band_section_setup.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        band = get_object_or_404(Band, pk=kwargs['pk'])
        context['band'] = band

        # set up the list of current sections
        sections = band.sections
        thelist = []
        for s in sections.all():
            if not s.is_default:
                name = s.name.replace('\"', '&quot;').replace("\'", "&apos;")
                thelist.append([name, s.id, name])
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
        writer.writerow([member.username, member.nickname,
                         member.email, member.phone, assoc.section.name])

    return response

@login_required
def archive_spreadsheet(request, pk):
    band = get_object_or_404(Band, pk=pk)

    if request.user.is_superuser:
        pass
    else:
        # if we're not active in the band, deny entry!
        assoc = Assoc.objects.filter(band=band, member=request.user).first()
        if assoc and assoc.status==AssocStatusChoices.CONFIRMED:
            pass
        else:
            raise PermissionDenied

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{band.shortname or band.name} archive.csv"'
    writer = csv.writer(response)
    writer.writerow(['date ', 'gig', 'contact'])
    for gig in Gig.objects.filter(band=band, is_archived=True):
        date = gig.date.strftime('%x')
        writer.writerow([date, gig.title, gig.contact.username])

    return response

@login_required
def member_emails(request, pk):
    band = get_object_or_404(Band, pk=pk)
    if not (band.is_admin(request.user) or request.user.is_superuser):
        raise PermissionDenied

    emails = ', '.join(a.member.email for a in band.confirmed_assocs)
    return render(request, 'band/member_emails.html', context={'band': band, 'emails': emails})
