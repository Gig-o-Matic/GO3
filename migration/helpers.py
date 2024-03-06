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
import logging
from band.models import Band
from member.models import Member
from django.contrib.auth.forms import PasswordResetForm
import go3.settings
from urllib.parse import urlparse

def send_migrated_user_password_reset(band_id, member_id):
  band = Band.objects.get(id=band_id)
  member = Member.objects.get(id=member_id)
  domain = urlparse(go3.settings.URL_BASE).netloc

  assert member.email

  logging.info("Sending password reset email to", member.email)
  form = PasswordResetForm({"email": member.email})
  
  assert form.is_valid()

  form.save(
    domain_override = domain,
    use_https=True,
    from_email=go3.settings.DEFAULT_FROM_EMAIL,
    subject_template_name="email/migration_password_reset_subject.txt",
    email_template_name="email/migration_password_reset_body.md",
    extra_email_context = {
      "band": band,
      "member": member,
    }
  )
