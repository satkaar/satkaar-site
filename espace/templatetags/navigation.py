"""Navigation de l'espace : une seule barre, aux couleurs du CRM Vanessa."""

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
    "contacts": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5a6.5 6.5 0 0 1 3.5 5.5"/>',
    "agenda": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18M8 14h2M14 14h2M8 17h2"/>',
}


def _page(cle, libelle, nom_url, actif, badge=0, titre_badge=""):
    return {"cle": cle, "libelle": libelle, "url": reverse(nom_url), "icone": mark_safe(ICONES[cle]),
            "actif": actif, "badge": badge, "titre_badge": titre_badge}


@register.simple_tag(takes_context=True)
def navigation_espace(context):
    """Pages de la barre : le tableau de bord pour un client ; toutes les rubriques pour l'équipe."""
    request = context["request"]
    correspondance = request.resolver_match
    application = correspondance.app_name if correspondance else ""
    nom = correspondance.url_name if correspondance else ""

    pages = [_page("tableau", "Tableau de bord", "espace:tableau", nom == "tableau")]
    if request.user.is_staff:
        from agenda.models import Evenement
        from contacts.models import Contact
        from courriel.models import Courriel

        non_lus = Courriel.objects.filter(dossier=Courriel.Dossier.RECEPTION, lu=False, corbeille=False).count()
        debut = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        du_jour = Evenement.objects.filter(debut__lt=debut + timedelta(days=1), fin__gt=debut).count()
        nouveaux = Contact.objects.filter(statut=Contact.Statut.LEAD).count()
        pages += [
            _page("statistiques", "Statistiques", "espace:statistiques", nom == "statistiques"),
            _page("mail", "Mail", "courriel:boite", application == "courriel", non_lus, "non lus" if non_lus > 1 else "non lu"),
            _page("agenda", "Agenda", "agenda:mois", application == "agenda", du_jour, "aujourd'hui"),
            _page("contacts", "Contacts", "contacts:liste", application == "contacts", nouveaux, "nouveaux leads" if nouveaux > 1 else "nouveau lead"),
        ]
    return pages
