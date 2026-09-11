import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def jsonld(donnees):
    """Sérialise des données schema.org pour une balise <script type="application/ld+json">.
    Les caractères <, > et & sont échappés : un texte ne peut pas refermer la balise."""
    texte = json.dumps(donnees, ensure_ascii=False, separators=(",", ":"))
    texte = texte.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return mark_safe(texte)
