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

from django.db.models.signals import post_save
from django.dispatch import receiver
from django_q.tasks import async_task
from .models import Member, MemberPreferences, Invite, EmailConfirmation
from go3.settings import IN_ETL


# signals to make sure a set of preferences is created for every user
@receiver(post_save, sender=Member)
def handle_user_preferences(sender, instance, created, **kwargs):
    if created:
        # for ETL from go2, don't do this because one will be created during import
        if IN_ETL is False:
            MemberPreferences.objects.create(member=instance)
    else:
        instance.preferences.save()


@receiver(post_save, sender=Invite)
def send_invite(sender, instance, created, **kwargs):
    if created:
        async_task("member.helpers.send_invite", instance)


@receiver(post_save, sender=EmailConfirmation)
def send_email_conf(sender, instance, created, **kwargs):
    if created:
        async_task("member.helpers.send_email_conf", instance)
