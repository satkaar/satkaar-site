from django.db.models.signals import post_save
from django.dispatch import receiver

from pages.models import DemandeDemonstration

from .import_demandes import importer
from .models import Contact, Note


@receiver(post_save, sender=DemandeDemonstration)
def demande_vers_lead(sender, instance, created, **kwargs):
    if created:
        importer(instance, Contact, Note)
