from django.http import HttpResponse
from .models import Member
from band.models import Band
from django.views import generic
from django.views.generic.edit import UpdateView as BaseUpdateView
from django.urls import reverse

def index(request):
    return HttpResponse("Hello, world. You're at the member index.")

class DetailView(generic.DetailView):
    model = Member
    template_name = 'member/member_detail.html'

    def get_context_data(self, **kwargs):

        the_member = self.object
        the_user = self.request.user

        ok_to_show = False
        same_band = False
        if the_member.id == the_user.id:
            is_me = True
            ok_to_show = True
        else:
            is_me = False
            
        # # find the bands this member is associated with
        # the_band_keys=assoc.get_band_keys_of_member_key(the_member_key=the_member.id, confirmed_only=True)
        the_member_bands = Band.objects.filter(id__in = [x.id for x in the_member.assocs.all()]) # TODO only show confirmed

        if is_me == False:
            # are we at least in the same band, or superuser?
            if the_user.is_superuser:
                ok_to_show = True
            # the_other_band_keys = assoc.get_band_keys_of_member_key(the_member_key=the_user.key, confirmed_only=True)
            # for b in the_other_band_keys:
            #     if b in the_band_keys:
            #         ok_to_show = True
            #         same_band = True
            #         break
            # if ok_to_show == False:
            #     # check to see if we're sharing our profile - if not, bail!
            #     if (the_member.preferences and the_member.preferences.share_profile == False) and the_user.is_superuser == False:
            #         return self.redirect('/')            

        # email_change = self.request.get('emailAddressChanged',False)
        # if email_change:
        #     email_change_msg='You have selected a new email address - check your inbox to verify!'
        # else:
        #     email_change_msg = None

        # if I'm not sharing my email, don't share my email
        show_email = False
        if the_member.id == the_user.id or the_user.is_superuser:
            show_email = True
        elif the_member.preferences.share_profile and the_member.preferences.share_email:
            show_email = True

        show_phone = False
        if the_member == the_user.id or the_user.is_superuser:
            show_phone = True
        else:
            # are we in the same band? If so, always show email and phone
            if same_band:
                show_phone = True
                show_email = True

        context = super().get_context_data(**kwargs)
        context['the_member_bands'] = the_member_bands
        context['show_email'] = show_email
        context['show_phone'] = show_phone
        context['member_is_me'] = the_user.id == the_member.id
        # template_args = {
        #     'the_member' : the_member,
        #     'the_band_keys' : the_band_keys,
        #     'member_is_me' : the_user == the_member,
        #     'email_change_msg' : email_change_msg,
        #     'show_email' : show_email,
        #     'show_phone' : show_phone
        # }

        return context


class UpdateView(BaseUpdateView):
    model = Member
    fields = ['email','username','nickname','phone','statement','images']
    def get_success_url(self):
        print('\n\nfoo\n\n')
        return reverse('member-detail', kwargs={'pk': self.object.id})

 