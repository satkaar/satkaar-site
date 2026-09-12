"""Navigation de l'espace, sur le modèle du CRM Vanessa : des rubriques dans le rail de gauche,
les pages de la rubrique choisie dans le volet voisin."""

from datetime import timedelta

from django import template
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe

register = template.Library()

ICONES = {
    "tableau": '<rect x="3" y="3" width="7" height="8" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="15" width="7" height="6" rx="1.5"/>',
    "statistiques": '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3.5 6.5 8.5 6.5 8.5-6.5"/>',
    "agenda": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18M8 14h2M14 14h2M8 17h2"/>',
}


def _page(libelle, nom_url, icone, actif, badge=0):
    return {"libelle": libelle, "url": reverse(nom_url), "icone": mark_safe(ICONES[icone]), "actif": actif, "badge": badge}


@register.simple_tag(takes_context=True)
def navigation_espace(context):
    request = context["request"]
    correspondance = request.resolver_match
    application = correspondance.app_name if correspondance else ""
    nom = correspondance.url_name if correspondance else ""

    if not request.user.is_staff:
        sections = [{"cle": "principal", "libelle": "Principal",
                     "pages": [_page("Tableau de bord", "espace:tableau", "tableau", nom == "tableau")]}]
    else:
        from agenda.models import Evenement
        from courriel.models import Courriel

        non_lus = Courriel.objects.filter(dossier=Courriel.Dossier.RECEPTION, lu=False, corbeille=False).count()
        debut = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        du_jour = Evenement.objects.filter(debut__lt=debut + timedelta(days=1), fin__gt=debut).count()
        sections = [
            {"cle": "pilotage", "libelle": "Pilotage", "pages": [
                _page("Tableau de bord", "espace:tableau", "tableau", nom == "tableau"),
                _page("Statistiques", "espace:statistiques", "statistiques", nom == "statistiques"),
            ]},
            {"cle": "communication", "libelle": "Communication", "pages": [
                _page("Mail", "courriel:boite", "mail", application == "courriel", non_lus),
                _page("Agenda", "agenda:semaine", "agenda", application == "agenda", du_jour),
            ]},
        ]
    for section in sections:
        section["actif"] = any(p["actif"] for p in section["pages"])
        section["badge"] = sum(p["badge"] for p in section["pages"])
        section["url"] = section["pages"][0]["url"]
    if not any(s["actif"] for s in sections):
        sections[0]["actif"] = True  # pages du compte (mot de passe) : première rubrique ouverte
    return sections
