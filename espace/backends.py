from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class ConnexionParCourriel(ModelBackend):
    """Les clients se connectent avec leur adresse courriel, sans tenir compte de la casse."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        courriel = (kwargs.get("email") or username or "").strip()
        if not courriel or password is None:
            return None
        Utilisateur = get_user_model()
        try:
            utilisateur = Utilisateur._default_manager.get(email__iexact=courriel)
        except Utilisateur.DoesNotExist:
            # Même coût qu'un vrai contrôle : on ne révèle pas si le compte existe.
            Utilisateur().set_password(password)
            return None
        except Utilisateur.MultipleObjectsReturned:
            return None
        if utilisateur.check_password(password) and self.user_can_authenticate(utilisateur):
            return utilisateur
        return None
