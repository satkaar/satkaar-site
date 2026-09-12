import csv
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from courriel.models import Courriel
from espace.acces import equipe

from .forms import ContactForm, NoteForm
from .models import Contact, Note

# Les trois logiciels suivis en priorité ; Katarina, le conseil et la formation restent filtrables.
PRODUITS_PHARES = ("isidor", "vanessa", "bernard")
ETAPES_PIPELINE = [s for s in Contact.Statut if s != Contact.Statut.PERDU]


def _filtrer(request):
    contacts = Contact.objects.select_related("responsable")
    produit = request.GET.get("produit", "")
    if produit in Contact.Produit.values:
        contacts = contacts.filter(produit=produit)
    else:
        produit = ""
    statut = request.GET.get("statut", "")
    if statut in Contact.Statut.values:
        contacts = contacts.filter(statut=statut)
    else:
        statut = ""
    recherche = request.GET.get("q", "").strip()
    if recherche:
        contacts = contacts.filter(Q(nom__icontains=recherche) | Q(organisation__icontains=recherche)
                                   | Q(courriel__icontains=recherche) | Q(ville__icontains=recherche))
    a_relancer = request.GET.get("relance") == "1"
    if a_relancer:
        contacts = contacts.filter(prochaine_relance__lte=timezone.localdate(), statut__in=Contact.EN_COURS)
    return contacts, produit, statut, recherche, a_relancer


def _somme(contacts):
    return sum((c.potentiel or Decimal(0) for c in contacts), Decimal(0))


def _resume_produit(cle, libelle, contacts):
    du_produit = [c for c in contacts if c.produit == cle]
    en_cours = [c for c in du_produit if c.en_cours]
    clients = [c for c in du_produit if c.statut == Contact.Statut.CLIENT]
    return {
        "cle": cle, "libelle": libelle, "leads": len(en_cours), "clients": len(clients),
        "potentiel": _somme(en_cours), "revenu": _somme(clients),
        "etapes": [{"cle": e.value, "libelle": e.label, "nombre": sum(1 for c in du_produit if c.statut == e)}
                   for e in ETAPES_PIPELINE],
    }


@equipe
def liste(request):
    contacts, produit, statut, recherche, a_relancer = _filtrer(request)
    vue = "liste" if request.GET.get("vue") == "liste" else "pipeline"
    tous = list(Contact.objects.all())
    libelles = dict(Contact.Produit.choices)
    trouves = list(contacts)
    aujourd_hui = timezone.localdate()
    colonnes = [{"cle": e.value, "libelle": e.label, "contacts": [c for c in trouves if c.statut == e],
                 "potentiel": _somme(c for c in trouves if c.statut == e)} for e in ETAPES_PIPELINE]
    return render(request, "contacts/liste.html", {
        "resumes": [_resume_produit(cle, libelles[cle], tous) for cle in PRODUITS_PHARES],
        "totaux": {
            "leads": sum(1 for c in tous if c.en_cours), "clients": sum(1 for c in tous if c.statut == Contact.Statut.CLIENT),
            "potentiel": _somme(c for c in tous if c.en_cours),
            "a_relancer": sum(1 for c in tous if c.en_cours and c.prochaine_relance and c.prochaine_relance <= aujourd_hui),
        },
        "contacts": trouves, "colonnes": colonnes, "perdus": sum(1 for c in trouves if c.statut == Contact.Statut.PERDU),
        "vue": vue, "produit": produit, "statut": statut, "recherche": recherche, "a_relancer": a_relancer,
        "produits": Contact.Produit.choices, "statuts": Contact.Statut.choices, "aujourdhui": aujourd_hui,
        "parametres": urlencode({k: v for k, v in (("produit", produit), ("statut", statut), ("q", recherche),
                                                    ("relance", "1" if a_relancer else "")) if v}),
    })


@equipe
def fiche(request, pk):
    contact = get_object_or_404(Contact.objects.select_related("responsable", "demande"), pk=pk)
    mails = Courriel.objects.none()
    if contact.courriel:
        mails = (Courriel.objects.filter(Q(expediteur_adresse__iexact=contact.courriel) | Q(destinataires__icontains=contact.courriel)
                                         | Q(copie__icontains=contact.courriel))
                 .filter(corbeille=False).order_by("-date")[:8])
    rendez_vous = reverse("agenda:ajouter") + "?" + urlencode({
        "titre": f"Rendez-vous {contact.get_produit_display()} — {contact.organisation or contact.nom}",
        "organisation": contact.organisation or contact.nom, "date": (timezone.localdate() + timedelta(days=1)).isoformat(),
    })
    return render(request, "contacts/fiche.html", {
        "contact": contact, "notes": contact.notes.select_related("auteur"), "mails": mails,
        "note_form": NoteForm(), "etapes": ETAPES_PIPELINE, "rendez_vous": rendez_vous,
        "index_etape": [e.value for e in ETAPES_PIPELINE].index(contact.statut) if contact.statut != Contact.Statut.PERDU else -1,
        "aujourdhui": timezone.localdate(),
    })


@equipe
def editer(request, pk=None):
    instance = get_object_or_404(Contact, pk=pk) if pk else None
    if request.method == "POST":
        form = ContactForm(request.POST, instance=instance)
        if form.is_valid():
            ancien = instance.statut if instance else None
            contact = form.save()
            if ancien and ancien != contact.statut:
                Note.objects.create(contact=contact, type=Note.Type.ETAPE, auteur=request.user,
                                    texte=f"Étape : {Contact.Statut(ancien).label} → {contact.get_statut_display()}")
            messages.success(request, "Fiche enregistrée." if instance else "Contact ajouté.")
            return redirect("contacts:fiche", contact.pk)
    else:
        initial = {"responsable": request.user.pk} if not instance else {}
        if not instance and request.GET.get("produit") in Contact.Produit.values:
            initial["produit"] = request.GET["produit"]
        form = ContactForm(instance=instance, initial=initial)
    return render(request, "contacts/editer.html", {"form": form, "instance": instance, "tailles": Contact.TAILLES})


@equipe
@require_POST
def changer_etape(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    statut = request.POST.get("statut")
    if statut not in Contact.Statut.values:
        raise Http404
    if statut != contact.statut:
        Note.objects.create(contact=contact, type=Note.Type.ETAPE, auteur=request.user,
                            texte=f"Étape : {contact.get_statut_display()} → {Contact.Statut(statut).label}")
        contact.statut = statut
        contact.save(update_fields=["statut", "modifie_le"])
        if statut == Contact.Statut.CLIENT:
            messages.success(request, f"{contact.nom} passe client {contact.get_produit_display()}.")
    return redirect(request.POST.get("suivant") if request.POST.get("suivant", "").startswith("/espace/contacts/") else reverse("contacts:fiche", args=[pk]))


@equipe
@require_POST
def ajouter_note(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    form = NoteForm(request.POST)
    if form.is_valid():
        note = form.save(commit=False)
        note.contact, note.auteur = contact, request.user
        note.save()
        contact.save(update_fields=["modifie_le"])
    else:
        messages.error(request, "Écrivez le contenu de l'échange avant de l'ajouter.")
    return redirect(reverse("contacts:fiche", args=[pk]) + "#echanges")


@equipe
@require_POST
def supprimer(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    contact.delete()
    messages.success(request, f"La fiche de {contact.nom} a été supprimée.")
    return redirect("contacts:liste")


@equipe
def export(request):
    contacts, *_ = _filtrer(request)
    reponse = HttpResponse(content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = f'attachment; filename="contacts-satkaar-{timezone.localdate():%Y-%m-%d}.csv"'
    reponse.write("﻿")  # BOM : Excel reconnaît l'UTF-8
    ecrivain = csv.writer(reponse, delimiter=";")
    ecrivain.writerow(["Nom", "Organisation", "Fonction", "Courriel", "Téléphone", "Commune", "Produit", "Étape", "Source",
                       "Taille", "Potentiel (€ HT/an)", "Prochaine relance", "Suivi par"])
    for c in contacts:
        ecrivain.writerow([c.nom, c.organisation, c.fonction, c.courriel, c.telephone, c.ville, c.get_produit_display(),
                           c.get_statut_display(), c.get_source_display(), c.taille or "",
                           str(c.potentiel).replace(".", ",") if c.potentiel is not None else "",
                           c.prochaine_relance.strftime("%d/%m/%Y") if c.prochaine_relance else "",
                           (c.responsable.get_full_name() or c.responsable.email) if c.responsable else ""])
    return reponse
