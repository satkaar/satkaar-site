from django import template

register = template.Library()
ESPACE_FINE = " "  # espace fine insécable, séparateur de milliers à la française


@register.filter
def nombre(valeur):
    if valeur is None:
        return "—"
    if isinstance(valeur, float) and not valeur.is_integer():
        return f"{valeur:,.1f}".replace(",", ESPACE_FINE).replace(".", ",")
    return f"{int(valeur):,}".replace(",", ESPACE_FINE)


@register.filter
def duree(secondes):
    """125 → « 2 min 05 s »."""
    if secondes is None:
        return "—"
    secondes = int(secondes)
    if secondes < 60:
        return f"{secondes} s"
    minutes, reste = divmod(secondes, 60)
    if minutes < 60:
        return f"{minutes} min {reste:02d} s"
    heures, minutes = divmod(minutes, 60)
    return f"{heures} h {minutes:02d}"


@register.filter
def millisecondes(valeur):
    """850 → « 850 ms » ; 2340 → « 2,3 s »."""
    if valeur is None:
        return "—"
    if valeur < 1000:
        return f"{round(valeur)} ms"
    return f"{valeur / 1000:.1f} s".replace(".", ",")


@register.filter
def variation(valeur):
    """12.5 → « +12,5 % » ; None → « — »."""
    if valeur is None:
        return "—"
    signe = "+" if valeur > 0 else ("−" if valeur < 0 else "")
    return f"{signe}{abs(valeur):.1f}".replace(".", ",").replace(",0", "") + " %"


@register.filter
def valeur_kpi(tuile):
    v, unite = tuile["valeur"], tuile["unite"]
    if unite == "s":
        return duree(v)
    if unite == "%":
        return f"{v:.1f}".replace(".", ",").replace(",0", "") + " %"
    return nombre(v)


@register.filter
def valeur_vitals(indicateur):
    v = indicateur["valeur"]
    if v is None:
        return "—"
    if indicateur["unite"] == "ms":
        return millisecondes(v)
    return f"{v:.2f}".replace(".", ",")


@register.filter
def get_item(dictionnaire, cle):
    return dictionnaire.get(cle) if dictionnaire else None
