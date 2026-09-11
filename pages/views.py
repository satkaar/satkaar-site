from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import formats
from django.views.decorators.http import require_POST

from .forms import DemandeDemonstrationForm
from .ia import ReformulationIndisponible, reformuler_message
from .models import DemandeDemonstration

# Garde-fous de la reformulation : l'adresse est publique et chaque appel est facturé.
REFORMULATION_LONGUEUR_MAX = 4000
REFORMULATION_APPELS_MAX = 10
REFORMULATION_FENETRE = 10 * 60  # secondes


def _page(gabarit):
    """Vue de contenu statique : le texte vit dans le gabarit."""

    def vue(request):
        return render(request, gabarit)

    return vue


accueil = _page("pages/accueil.html")
conseil = _page("pages/conseil.html")
formation = _page("pages/formation.html")
logiciels = _page("pages/logiciels.html")
isidor = _page("pages/isidor.html")
katarina = _page("pages/katarina.html")
vanessa = _page("pages/vanessa.html")
bernard = _page("pages/bernard.html")
souverainete = _page("pages/souverainete.html")
references = _page("pages/references.html")
a_propos = _page("pages/a_propos.html")

mentions_legales = _page("legal/mentions_legales.html")
confidentialite = _page("legal/confidentialite.html")
accessibilite = _page("legal/accessibilite.html")
cgu = _page("legal/cgu.html")


def _phrase_rappel(demande):
    """« le lundi 14 septembre vers 10 h 30 » ; None si aucun rappel n'est demandé."""
    if not (demande.rappel_jour or demande.rappel_heure):
        return None
    jour = formats.date_format(demande.rappel_jour, "l j F") if demande.rappel_jour else None
    heure = None
    if demande.rappel_heure:
        h = demande.rappel_heure
        heure = f"{h.hour} h {h.minute:02d}" if h.minute else f"{h.hour} h"
    if jour and heure:
        return f"le {jour} vers {heure}"
    return f"le {jour}" if jour else f"dès que possible, vers {heure}"


def contact(request):
    if request.method == "POST":
        form = DemandeDemonstrationForm(request.POST)
        if form.is_valid():
            demande = form.save()
            request.session["rappel"] = _phrase_rappel(demande)
            return redirect(f"{reverse('pages:contact')}?envoye=1")
    else:
        # Les pages Conseil et produits envoient ?sujet=… pour présélectionner la demande.
        sujet = request.GET.get("sujet")
        if sujet not in DemandeDemonstration.Sujet.values:
            sujet = None
        form = DemandeDemonstrationForm(initial={"sujet": sujet})

    envoye = request.GET.get("envoye") == "1"
    return render(
        request,
        "pages/contact.html",
        {
            "form": form,
            "envoye": envoye,
            "rappel": request.session.pop("rappel", None) if envoye else None,
        },
    )


@require_POST
def reformuler(request):
    """Propose une version reformulée du message ; le visiteur choisit de la garder ou non."""
    brouillon = request.POST.get("message", "").strip()
    if not brouillon:
        return JsonResponse({"erreur": "Écrivez ou dictez d'abord votre message."}, status=400)
    if len(brouillon) > REFORMULATION_LONGUEUR_MAX:
        return JsonResponse(
            {"erreur": f"Le message dépasse {REFORMULATION_LONGUEUR_MAX} caractères."}, status=400
        )

    cle = f"reformulation:{request.META.get('REMOTE_ADDR', '')}"
    cache.add(cle, 0, REFORMULATION_FENETRE)
    if cache.incr(cle) > REFORMULATION_APPELS_MAX:
        return JsonResponse(
            {"erreur": "Trop de reformulations demandées. Réessayez dans quelques minutes."},
            status=429,
        )

    try:
        texte = reformuler_message(brouillon)
    except ReformulationIndisponible:
        return JsonResponse(
            {"erreur": "La reformulation est indisponible pour le moment. Votre message est conservé."},
            status=503,
        )
    return JsonResponse({"texte": texte})
