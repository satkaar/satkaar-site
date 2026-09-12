from django import template

from ..models import Courriel

register = template.Library()


@register.simple_tag
def courriels_non_lus():
    return Courriel.objects.filter(dossier=Courriel.Dossier.RECEPTION, lu=False, corbeille=False).count()


@register.filter
def date_courte(valeur):
    """Heure pour aujourd'hui, jour et mois pour cette année, date complète sinon."""
    from django.utils import timezone
    from django.utils.dateformat import format as formater

    if not valeur:
        return ""
    locale, maintenant = timezone.localtime(valeur), timezone.localtime()
    if locale.date() == maintenant.date():
        return formater(locale, "H:i")
    if locale.year == maintenant.year:
        return formater(locale, "j M")
    return formater(locale, "d/m/Y")
