import csv
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
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

# Colonnes triables du tableau de prospection : clé publique → champs, dans l'ordre croissant
# de ce qui est affiché (l'âge croît quand la date de naissance décroît).
TRIS = {
    "nom": ("nom", "prenom"), "ville": ("ville",), "departement": ("departement", "ville"),
    "region": ("region", "departement"), "population": ("taille",), "age": ("-date_naissance",),
    "statut": ("statut", "ville"), "contact": ("date_contact",), "reponse": ("date_reponse",),
    "courriel": ("courriel",),
}
PAR_PAGE = 50

# Deux pipelines séparés : ce qui arrive, et ce qu'on va chercher.
PAGES = {
    Contact.Sens.ENTRANT: {"titre": "Contacts entrants", "sous_titre": "Demandes reçues et recommandations",
                           "vide": "Aucune demande entrante ne correspond à ces filtres.", "synthese": True,
                           "note": "Les demandes déposées sur le site arrivent ici automatiquement comme leads."},
    # La prospection va droit au pipeline : ni tuiles de synthèse, ni cartes par logiciel.
    Contact.Sens.SORTANT: {"titre": "Contacts sortants", "sous_titre": "Prospection menée par l'équipe",
                           "vide": "Aucun contact démarché ne correspond à ces filtres.", "synthese": False,
                           "note": "Ajoutez ici les organisations que vous démarchez : salons, LinkedIn, prospection directe."},
}


def _sens(valeur):
    return valeur if valeur in Contact.Sens.values else Contact.Sens.ENTRANT


def _filtrer(request, sens):
    contacts = Contact.objects.select_related("responsable").filter(sens=sens)
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


def _trier(contacts, demande):
    """« ville » ou « -ville » : la clé est vérifiée, le sens inversé champ par champ."""
    cle = (demande or "").lstrip("-")
    if cle not in TRIS:
        return contacts, "", False
    decroissant = (demande or "").startswith("-")
    champs = TRIS[cle]
    if decroissant:
        champs = tuple(c[1:] if c.startswith("-") else f"-{c}" for c in champs)
    return contacts.order_by(*champs), cle, decroissant


@equipe
def liste(request, sens=Contact.Sens.ENTRANT):
    contacts, produit, statut, recherche, a_relancer = _filtrer(request, sens)
    # La prospection s'ouvre sur le tableau ; les demandes entrantes sur le pipeline.
    defaut = "liste" if sens == Contact.Sens.SORTANT else "pipeline"
    vue = request.GET.get("vue") or defaut
    vue = "liste" if vue == "liste" else "pipeline"
    contacts, tri_cle, tri_decroissant = _trier(contacts, request.GET.get("tri") or ("-population" if sens == Contact.Sens.SORTANT else ""))
    tous = list(Contact.objects.filter(sens=sens))
    libelles = dict(Contact.Produit.choices)
    trouves = list(contacts)
    aujourd_hui = timezone.localdate()
    colonnes = [{"cle": e.value, "libelle": e.label, "contacts": [c for c in trouves if c.statut == e],
                 "potentiel": _somme(c for c in trouves if c.statut == e)} for e in ETAPES_PIPELINE]
    pagination = Paginator(trouves, PAR_PAGE).get_page(request.GET.get("page")) if vue == "liste" else None
    filtres = urlencode({k: v for k, v in (("produit", produit), ("statut", statut), ("q", recherche),
                                           ("relance", "1" if a_relancer else ""), ("vue", vue)) if v})
    return render(request, "contacts/liste.html", {
        "resumes": [_resume_produit(cle, libelles[cle], tous) for cle in PRODUITS_PHARES],
        "totaux": {
            "leads": sum(1 for c in tous if c.en_cours), "clients": sum(1 for c in tous if c.statut == Contact.Statut.CLIENT),
            "potentiel": _somme(c for c in tous if c.en_cours),
            "a_relancer": sum(1 for c in tous if c.en_cours and c.prochaine_relance and c.prochaine_relance <= aujourd_hui),
        },
        "contacts": pagination.object_list if pagination else trouves, "colonnes": colonnes,
        "pagination": pagination, "tri_cle": tri_cle, "tri_decroissant": tri_decroissant,
        "liens": filtres + "&" if filtres else "", "total": len(trouves),
        "perdus": sum(1 for c in trouves if c.statut == Contact.Statut.PERDU),
        "vue": vue, "produit": produit, "statut": statut, "recherche": recherche, "a_relancer": a_relancer,
        "sens": sens, "page": PAGES[sens], "note_estimation": any(c.estime for c in trouves), "url_liste": reverse("contacts:sortants" if sens == Contact.Sens.SORTANT else "contacts:liste"),
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
    request.contacts_sens = contact.sens  # pour que le menu montre le bon pipeline
    return render(request, "contacts/fiche.html", {
        "contact": contact, "page": PAGES[contact.sens],
        "url_liste": reverse("contacts:sortants" if contact.sens == Contact.Sens.SORTANT else "contacts:liste"), "notes": contact.notes.select_related("auteur"), "mails": mails,
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
        if not instance:
            initial["sens"] = _sens(request.GET.get("sens"))
            if request.GET.get("produit") in Contact.Produit.values:
                initial["produit"] = request.GET["produit"]
        form = ContactForm(instance=instance, initial=initial)
    sens = instance.sens if instance else _sens(request.GET.get("sens"))
    request.contacts_sens = sens
    return render(request, "contacts/editer.html", {
        "form": form, "instance": instance, "tailles": Contact.TAILLES, "page": PAGES[sens],
        "url_liste": reverse("contacts:sortants" if sens == Contact.Sens.SORTANT else "contacts:liste"),
    })


def _retour(request, contact):
    """Là d'où vient l'action : la page de liste demandée, sinon la fiche."""
    suivant = request.POST.get("suivant", "")
    return suivant if suivant.startswith("/espace/contacts/") else reverse("contacts:fiche", args=[contact.pk])


@equipe
@require_POST
def changer_etape(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    statut = request.POST.get("statut")
    if statut not in Contact.Statut.values:
        # Formulaire incomplet (champ non transmis, valeur inconnue) : on le dit, sans page d'erreur.
        messages.error(request, "Étape inconnue : la fiche n'a pas été modifiée.")
        return redirect(_retour(request, contact))
    if statut != contact.statut:
        Note.objects.create(contact=contact, type=Note.Type.ETAPE, auteur=request.user,
                            texte=f"Étape : {contact.get_statut_display()} → {Contact.Statut(statut).label}")
        contact.statut = statut
        champs = ["statut", "modifie_le"]
        # Premier geste vers la personne, puis premier retour de sa part : les dates se
        # remplissent toutes seules, et restent modifiables sur la fiche.
        aujourd_hui = timezone.localdate()
        if statut != Contact.Statut.LEAD and not contact.date_contact:
            contact.date_contact, champs = aujourd_hui, champs + ["date_contact"]
        if statut in (Contact.Statut.DEMO, Contact.Statut.PROPOSITION, Contact.Statut.CLIENT) and not contact.date_reponse:
            contact.date_reponse, champs = aujourd_hui, champs + ["date_reponse"]
        contact.save(update_fields=champs)
        if statut == Contact.Statut.CLIENT:
            messages.success(request, f"{contact.nom} passe client {contact.get_produit_display()}.")
    return redirect(_retour(request, contact))


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
    return redirect("contacts:sortants" if contact.sens == Contact.Sens.SORTANT else "contacts:liste")


def _jour(date):
    return date.strftime("%d/%m/%Y") if date else ""


@equipe
def export(request):
    """Le CSV reprend les colonnes de l'écran : celles de la prospection, ou celles du suivi commercial."""
    sens = _sens(request.GET.get("sens"))
    contacts, *_ = _filtrer(request, sens)
    contacts, *_ = _trier(contacts, request.GET.get("tri") or ("-population" if sens == Contact.Sens.SORTANT else ""))
    reponse = HttpResponse(content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = f'attachment; filename="contacts-satkaar-{timezone.localdate():%Y-%m-%d}.csv"'
    reponse.write("﻿")  # BOM : Excel reconnaît l'UTF-8
    ecrivain = csv.writer(reponse, delimiter=";")
    if sens == Contact.Sens.SORTANT:
        ecrivain.writerow(["Nom", "Prénom", "Ville", "Département", "Région", "Habitants", "Âge", "Statut",
                           "Contacté le", "Réponse le", "Courriel", "Téléphone", "Organisation", "Suivi par"])
        for c in contacts:
            ecrivain.writerow([c.nom, c.prenom, c.ville, c.departement, c.region, c.taille or "", c.age or "",
                               c.get_statut_display(), _jour(c.date_contact), _jour(c.date_reponse), c.courriel,
                               c.telephone, c.organisation,
                               (c.responsable.get_full_name() or c.responsable.email) if c.responsable else ""])
        return reponse
    ecrivain.writerow(["Nom", "Organisation", "Fonction", "Courriel", "Téléphone", "Commune", "Produit", "Étape", "Source",
                       "Taille", "Potentiel (€ HT/an)", "Prochaine relance", "Suivi par"])
    for c in contacts:
        ecrivain.writerow([c.nom_complet, c.organisation, c.fonction, c.courriel, c.telephone, c.ville, c.get_produit_display(),
                           c.get_statut_display(), c.get_source_display(), c.taille or "",
                           str(c.potentiel).replace(".", ",") if c.potentiel is not None else "",
                           _jour(c.prochaine_relance),
                           (c.responsable.get_full_name() or c.responsable.email) if c.responsable else ""])
    return reponse
