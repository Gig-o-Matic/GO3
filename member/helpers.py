"""
    This file is part of Gig-o-Matic

    Gig-o-Matic is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone, translation
from django.contrib.auth.decorators import login_required
from markdown import markdown

from lib.email import DEFAULT_SUBJECT, SUBJECT

@login_required
def motd_seen(request, pk):
    """ note that we've seen the motd """
    if request.user.id != pk:
        raise PermissionError('trying to mark MOTD seen for another user')

    request.user.motd_dirty = False
    request.user.save()

    return HttpResponse()


def prepare_email(member, template, context=None, **kw):
    if not context:
        context = dict()
    context['member'] = member

    with translation.override(member.preferences.locale):
        text = render_to_string(template, context)
    if text.startswith(SUBJECT):
        subject, text = [t.strip() for t in text[len(SUBJECT):].split('\n', 1)]
    else:
        subject = DEFAULT_SUBJECT
    html = markdown(text)

    message = EmailMultiAlternatives(subject, text, to=[member.email_line], **kw)
    message.attach_alternative(html, 'text/html')
    return message
