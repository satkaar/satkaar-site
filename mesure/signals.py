from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import Evenement


@receiver(user_logged_in)
def connexion(sender, request, user, **kwargs):
    # Les connexions de l'équipe Satkaar ne sont pas comptées.
    if not user.is_staff:
        Evenement.objects.create(type=Evenement.Type.CONNEXION, chemin="/espace/connexion/")
