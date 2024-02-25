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

from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from .models import Band, Assoc, Section
from gig.models import Plan
from gig.helpers import update_plan_default_section


@receiver(pre_save, sender=Band)
def set_condensed_name(sender, instance, **kwargs):
    instance.condensed_name = "".join(instance.name.split()).lower()


@receiver(post_save, sender=Band)
def set_default_section(sender, instance, created, **kwargs):
    if created:
        # if created or True: # for ETL from go2, always do this
        _ = Section.objects.create(
            name="No Section", band=instance, is_default=True, order=999
        )


@receiver(pre_delete, sender=Band)
def delete_band_parts(sender, instance, **kwargs):
    # when deleting a band, we need to delete the assocs first; otherwise when the sections delete and the
    # assocs reset to the default section, things go badly.
    l = Assoc.objects.filter(band=instance)
    l.delete()


@receiver(pre_save, sender=Assoc)
def set_initial_default_section(sender, instance, **kwargs):
    if instance.default_section is None:
        instance.default_section = instance.band.sections.get(is_default=True)


@receiver(post_save, sender=Assoc)
def set_plan_sections(sender, instance, created, **kwargs):

    # if this is a new assoc, make plans for the new member
    the_gigs = instance.band.gigs.future()
    for g in the_gigs:
        _ = g.member_plans

    # update any plans that rely on knowing the default section
    update_plan_default_section(instance)


@receiver(pre_delete, sender=Section)
def set_sections_of_assocs(sender, instance, **kwargs):
    # when a section gets deleted, set any assocs in the section to the band's default section before proceeding
    band_default_section = instance.band.sections.get(is_default=True)
    instance.default_assocs.update(default_section=band_default_section)

    # if any plans are using this section, set them back to the member's default section
    plans = Plan.objects.filter(plan_section=instance)
    for p in plans:
        p.plan_section = p.assoc.default_section
        p.save()

    plans = Plan.objects.filter(section=instance)
    for p in plans:
        p.section = p.assoc.default_section
        p.save()
