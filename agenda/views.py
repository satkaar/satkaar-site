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


def _aware(jour):
    return timezone.make_aware(datetime.combine(jour, time(0)))


def _colonne(reference, vue):
    """Colonne de gauche (comme le CRM) : nouvel événement, mini-calendrier et légende.
    La référence sert aussi au sélecteur Mois / Semaine / Jour du bandeau."""
    maintenant = timezone.localtime()
    premier = reference.replace(day=1)
    precedent, suivant = calendrier.mois_voisins(premier.year, premier.month)
    debut = _aware(calendrier.lundi_de(premier))
    return {
        "mini": calendrier.grille_mois(premier.year, premier.month, calendrier.elements(debut, debut + timedelta(days=42)),
                                       maintenant.date()),
        "mini_mois": premier, "mini_precedent": precedent, "mini_suivant": suivant,
        "categories": calendrier.CATEGORIES, "aujourdhui": maintenant.date(), "reference": reference, "vue": vue,
    }


@equipe
def mois(request, annee=None, mois=None):
    maintenant = timezone.localtime()
    premier = _jour(annee, mois) if annee else maintenant.date().replace(day=1)
    debut = _aware(calendrier.lundi_de(premier))
    precedent, suivant = calendrier.mois_voisins(premier.year, premier.month)
    reference = maintenant.date() if (premier.year, premier.month) == (maintenant.year, maintenant.month) else premier
    return render(request, "agenda/mois.html", {
        **_colonne(reference, "mois"), "premier": premier, "precedent": precedent, "suivant": suivant,
        "semaines": calendrier.grille_mois(premier.year, premier.month,
                                           calendrier.elements(debut, debut + timedelta(days=42)), maintenant.date()),
    })


def _grille(request, vue, reference):
    """Vue semaine (7 colonnes) ou jour (1 colonne), heure par heure."""
    maintenant = timezone.localtime()
    nb = 7 if vue == "semaine" else 1
    premier = calendrier.lundi_de(reference) if nb == 7 else reference
    debut = _aware(premier)
    jours = calendrier.colonnes(premier, nb, calendrier.elements(debut, debut + timedelta(days=nb)), maintenant)
    dernier = premier + timedelta(days=nb - 1)
    if nb == 1:
        titre = formater_date(premier, "l j F Y")
    elif premier.month == dernier.month:
        titre = f"{premier.day} – {formater_date(dernier, 'j F Y')}"
    else:
        titre = f"{formater_date(premier, 'j F')} – {formater_date(dernier, 'j F Y')}"
    return render(request, "agenda/grille.html", {
        **_colonne(reference, vue), "jours": jours, "titre": titre, "nb_jours": nb,
        "precedent": premier - timedelta(days=nb), "suivant": premier + timedelta(days=nb),
        "navigation": "agenda:semaine_du" if nb == 7 else "agenda:jour_du",
        "heures": range(calendrier.HEURE_DEBUT, calendrier.HEURE_FIN), "ouverture": calendrier.HEURE_OUVERTURE,
        "a_journee": any(j["journee"] for j in jours),
        "fuseau": "GMT" + formater_date(maintenant, "O")[:3],
    })


@equipe
def semaine(request, annee=None, mois=None, jour=None):
    return _grille(request, "semaine", _jour(annee, mois, jour) if annee else timezone.localdate())


@equipe
def jour(request, annee=None, mois=None, jour=None):
    return _grille(request, "jour", _jour(annee, mois, jour) if annee else timezone.localdate())


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
        **_colonne(debut.date(), "jour"), "evenement": element,
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
    reference = timezone.localtime(instance.debut).date() if instance else form.initial.get("date_debut", timezone.localdate())
    return render(request, "agenda/editer.html", {**_colonne(reference, "jour"), "form": form, "instance": instance})


@equipe
@require_POST
def supprimer(request, pk):
    element = get_object_or_404(Evenement, pk=pk)
    jour_evenement = timezone.localtime(element.debut).date()
    element.delete()
    messages.success(request, f"« {element.titre} » a été retiré de l'agenda.")
    return redirect("agenda:semaine_du", jour_evenement.year, jour_evenement.month, jour_evenement.day)


@equipe
def ics(request, pk):
    element = get_object_or_404(Evenement, pk=pk)
    reponse = HttpResponse(calendrier.ics(element), content_type="text/calendar; charset=utf-8")
    reponse["Content-Disposition"] = f'attachment; filename="satkaar-agenda-{element.pk}.ics"'
    return reponse
