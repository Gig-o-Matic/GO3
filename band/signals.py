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
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Band, Assoc
from gig.helpers import update_plan_default_section

@receiver(pre_save, sender=Band)
def my_handler(sender, instance, **kwargs):
    instance.condensed_name = ''.join(instance.name.split()).lower()

@receiver(post_save, sender=Assoc)
def update_plan_section(sender, instance, **kwargs):
    # update any plans that rely on knowing the default section
    update_plan_default_section(instance)

