import json
from urllib.parse import urlparse

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import detection
from .analyse import analyser
from .graphiques import colonnes, courbe, mini_courbe
from .middleware import EXCLUS
from .models import Evenement, Mesure
from .sante import auditer

PERIODES = {"7": "7 derniers jours", "30": "30 derniers jours", "90": "90 derniers jours", "365": "12 derniers mois"}
TAILLE_MAX = 4096
ENVOIS_MAX = 120  # par visiteur et par tranche de 10 minutes


def _entier(valeur, maximum):
    try:
        return max(0, min(int(float(valeur)), maximum))
    except (TypeError, ValueError):
        return None


@csrf_exempt  # envoyé par navigator.sendBeacon, sans jeton ; l'origine est vérifiée ci-dessous
@require_POST
def collecte(request):
    """Reçoit les mesures du navigateur : engagement, performance et événements."""
    vide = HttpResponse(status=204)
    origine = urlparse(request.META.get("HTTP_ORIGIN") or request.META.get("HTTP_REFERER", "")).netloc
    if origine != request.get_host() or len(request.body) > TAILLE_MAX:
        return HttpResponse(status=400)
    ua = request.META.get("HTTP_USER_AGENT", "")
    if detection.robot(ua) or detection.refuse_le_suivi(request):
        return vide
    if request.user.is_authenticated and request.user.is_staff:
        return vide

    visiteur = detection.empreinte(request)
    cle = f"mesure:envois:{visiteur}"
    cache.add(cle, 0, 600)
    if cache.incr(cle) > ENVOIS_MAX:
        return vide

    try:
        donnees = json.loads(request.body)
    except ValueError:
        return HttpResponse(status=400)
    chemin = str(donnees.get("chemin", ""))[:300]
    if not chemin.startswith("/"):
        return HttpResponse(status=400)
    if chemin.startswith(EXCLUS):
        return vide

    type_ = donnees.get("type")
    if type_ == "page":
        cls = donnees.get("cls")
        Mesure.objects.create(
            chemin=chemin, visiteur=visiteur,
            temps_actif_s=_entier(donnees.get("temps_actif"), 6 * 3600) or 0,
            defilement=_entier(donnees.get("defilement"), 100) or 0,
            lcp_ms=_entier(donnees.get("lcp"), 60000),
            cls=round(min(max(float(cls), 0), 10), 4) if isinstance(cls, (int, float)) else None,
            inp_ms=_entier(donnees.get("inp"), 60000),
            fcp_ms=_entier(donnees.get("fcp"), 60000),
            ttfb_ms=_entier(donnees.get("ttfb"), 60000),
        )
    elif type_ in Evenement.Type.values and type_ not in ("connexion", "telechargement", "reformulation"):
        Evenement.objects.create(type=type_, chemin=chemin, visiteur=visiteur,
                                 cible=str(donnees.get("cible", ""))[:200])
    return vide


@login_required
def statistiques(request):
    if not request.user.is_staff:
        raise Http404
    periode = request.GET.get("periode", "30")
    if periode not in PERIODES:
        periode = "30"
    resultats = analyser(int(periode))
    sante = auditer(request.get_host(), forcer=request.GET.get("audit") == "1")
    titres = sante["titres"]
    for liste in (resultats["pages"], resultats["entrees"], resultats["sorties"]):
        for ligne in liste:
            chemin = ligne.get("chemin") or ligne.get("libelle")
            ligne["titre"] = titres.get(chemin, "")

    serie = resultats["serie"]
    for tuile in resultats["kpi"]:
        cle = {"visiteurs": "visiteurs", "visites": "visites", "pages_vues": "pages_vues"}.get(tuile["cle"])
        tuile["mini"] = mini_courbe([p[cle] for p in serie]) if cle else None

    graphique = courbe(serie, "visites")
    return render(request, "espace/statistiques.html", {
        "r": resultats,
        "sante": sante,
        "periode": periode,
        "periodes": PERIODES,
        "courbe": graphique,
        # Dessinées à la largeur réelle des cartes (moitié de page) pour que le texte garde sa taille.
        "colonnes_heures": colonnes(resultats["heures"], largeur=520, hauteur=190),
        "colonnes_jours": colonnes(resultats["jours_semaine"], largeur=520, hauteur=190),
        "points_courbe": [{"x": p["x"], "y": p["y"], "t": p["texte"], "v": p["valeur"]}
                          for p in graphique["points"]],
    })
