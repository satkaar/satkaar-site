from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import PieceJointe


@receiver(post_delete, sender=PieceJointe)
def effacer_fichier(sender, instance, **kwargs):
    """Une pièce jointe retirée (y compris avec sa boîte) ne laisse pas son fichier sur le disque."""
    if instance.fichier:
        instance.fichier.delete(save=False)
