from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import Http404


def equipe(vue):
    """Réservé à l'équipe Satkaar : un client connecté reçoit une page introuvable."""

    @login_required
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        if not request.user.is_staff:
            raise Http404
        return vue(request, *args, **kwargs)

    return enveloppe
