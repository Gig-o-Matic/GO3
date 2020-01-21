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
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import Band, Assoc, Section
from gig.helpers import update_plan_default_section

@receiver(pre_save, sender=Band)
def set_condensed_name(sender, instance, **kwargs):
    instance.condensed_name = ''.join(instance.name.split()).lower()

@receiver(post_save, sender=Band)
def set_default_section(sender, instance, created, **kwargs):
    if created:
        s = Section.objects.create(name=None, band=instance, is_default=True)

@receiver(pre_save, sender=Assoc)
def set_initial_default_section(sender, instance, **kwargs):
    if instance.default_section is None:
        instance.default_section = instance.band.sections.get(is_default=True)

@receiver(post_save, sender=Assoc)
def set_plan_sections(sender, instance, **kwargs):
    # update any plans that rely on knowing the default section
    update_plan_default_section(instance)
