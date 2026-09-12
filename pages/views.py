from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import formats
from django.views.decorators.http import require_POST

from mesure.models import Evenement

from . import seo
from .forms import DemandeDemonstrationForm
from .ia import ReformulationIndisponible, reformuler_message
from .models import DemandeDemonstration

# Garde-fous de la reformulation : l'adresse est publique et chaque appel est facturé.
REFORMULATION_LONGUEUR_MAX = 4000
REFORMULATION_APPELS_MAX = 10
REFORMULATION_FENETRE = 10 * 60  # secondes


def _page(gabarit, contexte=None):
    """Vue de contenu statique : le texte vit dans le gabarit. `contexte(request)` fournit les
    données de référencement propres à la page (FAQ, fil d'Ariane, fiches schema.org)."""

    def vue(request):
        return render(request, gabarit, contexte(request) if contexte else {})

    return vue


def _seo(fil=(), faq=None, logiciel=None):
    def contexte(request):
        donnees = {"jsonld": []}
        if fil:
            donnees["jsonld"].append(seo.fil_ariane(request, fil))
        if logiciel:
            donnees["jsonld"].append(seo.logiciel(request, logiciel))
        if faq:
            donnees["faq"] = seo.faq(request, faq)
            donnees["jsonld"].append(donnees["faq"]["jsonld"])
        return donnees

    return contexte


accueil = _page("pages/accueil.html", _seo(faq="accueil"))
conseil = _page("pages/conseil.html", _seo([("Conseil", "pages:conseil")], faq="conseil"))
formation = _page("pages/formation.html", _seo([("Formation", "pages:formation")], faq="formation"))
logiciels = _page("pages/logiciels.html", _seo([("Logiciels", "pages:logiciels")], faq="logiciels"))
isidor = _page("pages/isidor.html", _seo([("Logiciels", "pages:logiciels"), ("Isidor", "pages:isidor")], logiciel="isidor"))
katarina = _page("pages/katarina.html", _seo([("Logiciels", "pages:logiciels"), ("Katarina", "pages:katarina")], logiciel="katarina"))
vanessa = _page("pages/vanessa.html", _seo([("Logiciels", "pages:logiciels"), ("Vanessa", "pages:vanessa")], logiciel="vanessa"))
bernard = _page("pages/bernard.html", _seo([("Logiciels", "pages:logiciels"), ("Bernard", "pages:bernard")], logiciel="bernard"))
souverainete = _page("pages/souverainete.html", _seo([("Souveraineté et conformité", "pages:souverainete")]))
references = _page("pages/references.html", _seo([("Références", "pages:references")]))
a_propos = _page("pages/a_propos.html", _seo([("À propos", "pages:a_propos")]))

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
    Evenement.objects.create(type=Evenement.Type.REFORMULATION, chemin=reverse("pages:contact"))
    return JsonResponse({"texte": texte})


def _texte(gabarit, request, **contexte):
    contexte.setdefault("racine", request.build_absolute_uri("/"))
    corps = render_to_string(gabarit, contexte, request=request).strip() + "\n"
    return HttpResponse(corps, content_type="text/plain; charset=utf-8")


def robots(request):
    if settings.NOINDEX:
        return HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain; charset=utf-8")
    return _texte("robots.txt", request)


def llms(request):
    """Résumé du site pour les assistants IA (convention llms.txt)."""
    return _texte("llms.txt", request, faq=seo.FAQ, courriel=seo.COURRIEL)
