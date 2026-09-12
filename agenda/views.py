from datetime import date, datetime, time, timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateformat import format as formater_date
from django.views.decorators.http import require_POST

from espace.acces import equipe

from . import calendrier
from .forms import EvenementForm
from .models import Evenement


def _jour(annee, mois, jour=1):
    try:
        return date(annee, mois, jour)
    except ValueError:
        raise Http404 from None


def _colonne(reference, lundi=None):
    """Colonne de gauche : mini-calendrier du mois, légende et prochains rendez-vous."""
    maintenant = timezone.localtime()
    premier = reference.replace(day=1)
    precedent, suivant = calendrier.mois_voisins(premier.year, premier.month)
    debut = timezone.make_aware(datetime.combine(calendrier.lundi_de(premier), time(0)))
    trouves = calendrier.elements(debut, debut + timedelta(days=42))
    prochains = [e for e in calendrier.elements(maintenant, maintenant + timedelta(days=60))
                 if e.fin > maintenant and not e.fait][:6]
    return {
        "mini": calendrier.grille_mois(premier.year, premier.month, trouves, maintenant.date(), lundi),
        "mini_mois": premier, "mini_precedent": precedent, "mini_suivant": suivant,
        "categories": calendrier.CATEGORIES, "prochains": prochains, "aujourdhui": maintenant.date(),
    }


@equipe
def semaine(request, annee=None, mois=None, jour=None):
    maintenant = timezone.localtime()
    reference = _jour(annee, mois, jour) if annee else maintenant.date()
    lundi = calendrier.lundi_de(reference)
    debut = timezone.make_aware(datetime.combine(lundi, time(0)))
    jours = calendrier.semaine(lundi, calendrier.elements(debut, debut + timedelta(days=7)), maintenant)
    return render(request, "agenda/semaine.html", {
        **_colonne(reference, lundi), "vue": "semaine", "jours": jours, "lundi": lundi, "dimanche": lundi + timedelta(days=6),
        "precedente": lundi - timedelta(days=7), "suivante": lundi + timedelta(days=7),
        "heures": range(calendrier.HEURE_DEBUT, calendrier.HEURE_FIN),
        "a_journee": any(j["journee"] for j in jours),
    })


@equipe
def mois(request, annee=None, mois=None):
    maintenant = timezone.localtime()
    premier = _jour(annee, mois) if annee else maintenant.date().replace(day=1)
    debut = timezone.make_aware(datetime.combine(calendrier.lundi_de(premier), time(0)))
    trouves = calendrier.elements(debut, debut + timedelta(days=42))
    precedent, suivant = calendrier.mois_voisins(premier.year, premier.month)
    return render(request, "agenda/mois.html", {
        **_colonne(premier), "vue": "mois", "premier": premier, "precedent": precedent, "suivant": suivant,
        "semaines": calendrier.grille_mois(premier.year, premier.month, trouves, maintenant.date()),
    })


def _invitation(evenement):
    """Lien vers la rédaction d'un mail d'invitation prérempli (module Mail)."""
    debut, fin = timezone.localtime(evenement.debut), timezone.localtime(evenement.fin)
    if evenement.journee_entiere:
        quand = formater_date(debut, "l j F Y")
    else:
        quand = f"{formater_date(debut, 'l j F Y')}, de {debut:%H:%M} à {fin:%H:%M}"
    lignes = ["Bonjour,", "", f"Je vous propose de nous retrouver le {quand}.", ""]
    if evenement.lieu:
        lignes.append(f"Lieu : {evenement.lieu}")
    if evenement.lien_visio:
        lignes.append(f"Visio : {evenement.lien_visio}")
    if evenement.description:
        lignes += ["", evenement.description]
    lignes += ["", "Bien cordialement,"]
    return reverse("courriel:rediger") + "?" + urlencode({
        "sujet": f"Invitation : {evenement.titre} — {formater_date(debut, 'j F')}", "texte": "\n".join(lignes)})


@equipe
def evenement(request, pk):
    element = get_object_or_404(Evenement.objects.prefetch_related("participants"), pk=pk)
    debut = timezone.localtime(element.debut)
    return render(request, "agenda/evenement.html", {
        **_colonne(debut.date(), calendrier.lundi_de(debut.date())), "vue": "semaine", "evenement": element,
        "invitation": _invitation(element), "debut": debut, "fin": timezone.localtime(element.fin),
        "fin_affichee": timezone.localtime(element.fin) - (timedelta(days=1) if element.journee_entiere else timedelta()),
    })


@equipe
def editer(request, pk=None):
    instance = get_object_or_404(Evenement, pk=pk) if pk else None
    if request.method == "POST":
        form = EvenementForm(request.POST, instance=instance)
        if form.is_valid():
            element = form.save(commit=False)
            if not element.pk:
                element.cree_par = request.user
            element.save()
            form.save_m2m()
            messages.success(request, "Événement enregistré." if instance else "Événement ajouté à l'agenda.")
            return redirect("agenda:evenement", element.pk)
    else:
        initial = {}
        if not instance:
            try:
                initial["date_debut"] = date.fromisoformat(request.GET.get("date", ""))
            except ValueError:
                initial["date_debut"] = timezone.localdate()
            try:
                heure = time.fromisoformat(request.GET.get("heure", ""))
            except ValueError:
                heure = time(9)
            initial.update({"heure_debut": heure, "heure_fin": (datetime.combine(date.today(), heure) + timedelta(hours=1)).time(),
                            "participants": [request.user.pk]})
        form = EvenementForm(instance=instance, initial=initial)
    reference = timezone.localtime(instance.debut).date() if instance else timezone.localdate()
    return render(request, "agenda/editer.html", {**_colonne(reference), "vue": "semaine", "form": form, "instance": instance})


@equipe
@require_POST
def supprimer(request, pk):
    element = get_object_or_404(Evenement, pk=pk)
    jour = timezone.localtime(element.debut).date()
    element.delete()
    messages.success(request, f"« {element.titre} » a été retiré de l'agenda.")
    return redirect("agenda:semaine_du", jour.year, jour.month, jour.day)


@equipe
def ics(request, pk):
    element = get_object_or_404(Evenement, pk=pk)
    reponse = HttpResponse(calendrier.ics(element), content_type="text/calendar; charset=utf-8")
    reponse["Content-Disposition"] = f'attachment; filename="satkaar-agenda-{element.pk}.ics"'
    return reponse
