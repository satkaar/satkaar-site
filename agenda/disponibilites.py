"""Créneaux de rappel déjà pris, pour le formulaire de contact : un créneau occupé dans l'agenda
de l'équipe, ou déjà demandé par un autre visiteur, ne peut pas être réservé deux fois."""

from datetime import datetime, time, timedelta

from django.utils import timezone

from pages.models import DemandeDemonstration

from .models import Evenement

DUREE_RAPPEL = timedelta(minutes=30)


def _aware(jour, heure=time(0)):
    return timezone.make_aware(datetime.combine(jour, heure))


def creneaux_pris(jours, heures):
    """{"2026-09-14": ["09:00", "09:30"], …} pour les jours proposés ; un jour entièrement pris
    (événement sur la journée entière, ou toutes les heures occupées) liste toutes les heures."""
    if not jours:
        return {}
    debut, fin = _aware(jours[0]), _aware(jours[-1] + timedelta(days=1))
    evenements = list(Evenement.objects.filter(debut__lt=fin, fin__gt=debut).only("debut", "fin", "journee_entiere"))
    demandes = set(DemandeDemonstration.objects.filter(rappel_jour__in=jours, rappel_heure__isnull=False)
                   .values_list("rappel_jour", "rappel_heure"))
    pris = {}
    for jour in jours:
        debut_jour, fin_jour = _aware(jour), _aware(jour + timedelta(days=1))
        du_jour = [e for e in evenements if e.debut < fin_jour and e.fin > debut_jour]
        if any(e.journee_entiere for e in du_jour):
            occupees = list(heures)
        else:
            occupees = []
            for heure in heures:
                h = time.fromisoformat(heure)
                creneau_debut = _aware(jour, h)
                creneau_fin = creneau_debut + DUREE_RAPPEL
                if (jour, h) in demandes or any(e.debut < creneau_fin and e.fin > creneau_debut for e in du_jour):
                    occupees.append(heure)
        if occupees:
            pris[jour.isoformat()] = occupees
    return pris
