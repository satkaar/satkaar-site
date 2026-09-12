import mimetypes
import re
from datetime import timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateformat import format as formater_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from espace.acces import equipe

from . import protocoles
from .forms import FOURNISSEURS, CompteForm, RedactionForm
from .models import CompteCourriel, Courriel, PieceJointe

PAR_PAGE = 40
RELEVE_AUTO = timedelta(minutes=5)

DOSSIERS = {
    "reception": ("Boîte de réception", Q(dossier=Courriel.Dossier.RECEPTION, corbeille=False)),
    "etoiles": ("Étoilés", Q(etoile=True, corbeille=False)),
    "envoyes": ("Envoyés", Q(dossier=Courriel.Dossier.ENVOYES, corbeille=False)),
    "corbeille": ("Corbeille", Q(corbeille=True)),
}
ACTIONS = {
    "etoile": {"etoile": True}, "sans_etoile": {"etoile": False},
    "lu": {"lu": True}, "non_lu": {"lu": False},
    "corbeille": {"corbeille": True}, "restaurer": {"corbeille": False},
}


def _barre(dossier_actif, **extra):
    return {
        "dossier_actif": dossier_actif,
        "comptes": CompteCourriel.objects.all(),
        "nb_non_lus": Courriel.objects.filter(dossier=Courriel.Dossier.RECEPTION, lu=False, corbeille=False).count(),
        "nb_etoiles": Courriel.objects.filter(etoile=True, corbeille=False).count(),
        **extra,
    }


@equipe
def boite(request, dossier="reception"):
    if dossier not in DOSSIERS:
        raise Http404
    titre, filtre = DOSSIERS[dossier]
    liste = Courriel.objects.filter(filtre).select_related("compte").annotate(nb_pieces=Count("pieces_jointes")).order_by("-date", "-pk")
    compte = CompteCourriel.objects.filter(pk=request.GET.get("compte")).first() if request.GET.get("compte", "").isdigit() else None
    if compte:
        liste = liste.filter(compte=compte)
    recherche = request.GET.get("q", "").strip()
    if recherche:
        liste = liste.filter(Q(sujet__icontains=recherche) | Q(expediteur_nom__icontains=recherche)
                             | Q(expediteur_adresse__icontains=recherche) | Q(destinataires__icontains=recherche)
                             | Q(texte__icontains=recherche))
    page = _page(liste, request.GET.get("page"))
    limite = timezone.now() - RELEVE_AUTO
    releve_auto = CompteCourriel.objects.filter(actif=True).filter(
        Q(derniere_releve__isnull=True) | Q(derniere_releve__lt=limite)).exists()
    return render(request, "courriel/boite.html", _barre(
        dossier if not compte else f"compte-{compte.pk}", titre=titre, dossier=dossier, page=page, compte=compte,
        recherche=recherche, releve_auto=releve_auto and dossier == "reception",
    ))


def _page(liste, numero):
    return Paginator(liste, PAR_PAGE).get_page(numero)


def _document_isole(html, images):
    """Le HTML d'un courriel, affiché dans un cadre sans script ; images distantes bloquées par défaut
    (elles servent souvent à pister l'ouverture du message)."""
    sources = "data: cid:" + (" https: http:" if images else "")
    politique = f"default-src 'none'; style-src 'unsafe-inline'; font-src data:; img-src {sources}"
    return (
        f'<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="{politique}">'
        '<base target="_blank"><style>body{margin:0;font:15px/1.6 system-ui,sans-serif;color:#0e2c4b;'
        'overflow-wrap:anywhere}img{max-width:100%;height:auto}table{max-width:100%}</style>' + html
    )


@equipe
def lire(request, pk):
    courriel = get_object_or_404(Courriel.objects.select_related("compte"), pk=pk)
    if not courriel.lu:
        Courriel.objects.filter(pk=pk).update(lu=True)
    images = request.GET.get("images") == "1"
    a_images_distantes = bool(re.search(r"""<img[^>]+src=["']?https?:""", courriel.html, re.I)) if courriel.html else False
    dossier = "corbeille" if courriel.corbeille else ("envoyes" if courriel.envoye else "reception")
    return render(request, "courriel/lire.html", _barre(
        dossier, courriel=courriel, pieces=courriel.pieces_jointes.all(),
        document=_document_isole(courriel.html, images) if courriel.html else "",
        images=images, a_images_distantes=a_images_distantes,
    ))


@equipe
@require_POST
def agir(request, pk):
    action = request.POST.get("action")
    if action not in ACTIONS:
        raise Http404
    Courriel.objects.filter(pk=pk).update(**ACTIONS[action])
    suivant = request.POST.get("suivant", "")
    if action == "corbeille":
        messages.success(request, "Message placé dans la corbeille.")
    if not url_has_allowed_host_and_scheme(suivant, allowed_hosts={request.get_host()}):
        suivant = reverse("courriel:boite")
    return redirect(suivant)


def _sujet(prefixe, sujet):
    sujet = sujet or "(sans objet)"
    return sujet if re.match(rf"^{prefixe}\s*:", sujet, re.I) else f"{prefixe}: {sujet}"


def _brouillon(origine, mode, compte):
    """Valeurs de départ du formulaire : signature, destinataires et message cité."""
    signature = f"\n\n-- \n{compte.signature}" if compte and compte.signature else ""
    if not origine:
        return {"compte": compte, "texte": signature}
    quand = formater_date(timezone.localtime(origine.date), "j F Y à H:i")
    auteur = origine.expediteur_nom or origine.expediteur_adresse
    if mode == "transferer":
        entete = (f"---------- Message transféré ----------\nDe : {auteur} <{origine.expediteur_adresse}>\n"
                  f"Date : {quand}\nObjet : {origine.sujet}\nÀ : {origine.destinataires}\n\n")
        return {"compte": compte, "sujet": _sujet("Tr", origine.sujet), "texte": f"{signature}\n\n{entete}{origine.texte}"}

    if origine.envoye:
        a = origine.destinataires
    else:
        a = origine.repondre_a or origine.expediteur_adresse
    copie = ""
    if mode == "repondre_tous":
        autres = [x.strip() for x in f"{origine.destinataires},{origine.copie}".split(",") if x.strip()]
        exclues = {compte.adresse.lower(), a.lower()}
        copie = ", ".join(dict.fromkeys(x for x in autres if x.lower() not in exclues))
    citation = "\n".join(f"> {ligne}" for ligne in origine.texte.splitlines())
    return {"compte": compte, "a": a, "copie": copie, "sujet": _sujet("Re", origine.sujet),
            "texte": f"{signature}\n\nLe {quand}, {auteur} a écrit :\n{citation}"}


@equipe
def rediger(request):
    comptes = CompteCourriel.objects.filter(actif=True)
    if not comptes.exists():
        messages.info(request, "Ajoutez d'abord une boîte mail pour pouvoir écrire.")
        return redirect("courriel:comptes")
    donnees = request.POST if request.method == "POST" else request.GET
    mode = donnees.get("mode", "")
    origine = None
    if mode in ("repondre", "repondre_tous", "transferer") and str(donnees.get("origine", "")).isdigit():
        origine = get_object_or_404(Courriel, pk=donnees["origine"])
    else:
        mode = ""

    if request.method == "POST":
        form = RedactionForm(request.POST, request.FILES)
        if form.is_valid():
            d = form.cleaned_data
            pieces = [{"nom": f.name, "type_mime": f.content_type or mimetypes.guess_type(f.name)[0] or "application/octet-stream",
                       "contenu": f.read()} for f in d["pieces"]]
            if origine and mode == "transferer" and request.POST.get("joindre_origine"):
                for piece in origine.pieces_jointes.all():
                    with piece.fichier.open("rb") as fichier:
                        pieces.append({"nom": piece.nom, "type_mime": piece.type_mime, "contenu": fichier.read()})
            reponse = origine if origine and mode.startswith("repondre") else None
            try:
                envoye = protocoles.envoyer(
                    d["compte"], d["a"], d["sujet"], d["texte"], copie=d["copie"], copie_cachee=d["copie_cachee"],
                    pieces=pieces, en_reponse_a=reponse.message_id if reponse else "",
                    references=reponse.references if reponse else "", utilisateur=request.user,
                )
            except protocoles.ErreurCourriel as erreur:
                form.add_error(None, str(erreur))
            else:
                messages.success(request, f"Message envoyé à {', '.join(d['a'])}.")
                return redirect("courriel:lire", envoye.pk)
    else:
        compte = origine.compte if origine and origine.compte.actif else comptes.first()
        initial = _brouillon(origine, mode, compte)
        if not origine:
            # Préremplissage depuis un autre écran (invitation envoyée depuis l'agenda…).
            initial.update({cle: request.GET[cle][:500] for cle in ("a", "sujet") if request.GET.get(cle)})
            if request.GET.get("texte"):
                initial["texte"] = request.GET["texte"][:5000] + initial["texte"]
        form = RedactionForm(initial=initial)

    return render(request, "courriel/rediger.html", _barre(
        "rediger", form=form, origine=origine, mode=mode,
        pieces_origine=origine.pieces_jointes.all() if origine and mode == "transferer" else [],
        signatures={c.pk: c.signature for c in comptes},
    ))


@equipe
@require_POST
def relever(request):
    nouveaux, erreurs = 0, []
    for compte in CompteCourriel.objects.filter(actif=True):
        try:
            nouveaux += protocoles.relever(compte)
        except protocoles.ErreurCourriel as erreur:
            CompteCourriel.objects.filter(pk=compte.pk).update(derniere_erreur=str(erreur)[:300], derniere_releve=timezone.now())
            erreurs.append(f"{compte} : {erreur}")
    if request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"nouveaux": nouveaux, "erreurs": erreurs})
    for erreur in erreurs:
        messages.error(request, erreur)
    if not erreurs:
        messages.success(request, f"{nouveaux} nouveau{'x' if nouveaux > 1 else ''} message{'s' if nouveaux > 1 else ''}." if nouveaux else "Aucun nouveau message.")
    return redirect("courriel:boite")


@equipe
def comptes(request):
    liste = CompteCourriel.objects.annotate(nb=Count("courriels"))
    return render(request, "courriel/comptes.html", _barre("comptes", liste=liste))


@equipe
def compte(request, pk=None):
    instance = get_object_or_404(CompteCourriel, pk=pk) if pk else None
    depart = None if instance else {**{k: v for k, v in FOURNISSEURS["ovh"].items() if k != "libelle"}, "nom_expediteur": "Satkaar"}
    form = CompteForm(request.POST or None, instance=instance, initial=depart)
    if request.method == "POST" and form.is_valid():
        boite_mail = form.save()
        try:
            protocoles.tester(boite_mail)
        except protocoles.ErreurCourriel as erreur:
            CompteCourriel.objects.filter(pk=boite_mail.pk).update(derniere_erreur=str(erreur)[:300])
            messages.warning(request, f"Boîte enregistrée, mais la connexion échoue : {erreur}")
            return redirect("courriel:comptes")
        CompteCourriel.objects.filter(pk=boite_mail.pk).update(derniere_erreur="")
        if instance:
            messages.success(request, "Boîte enregistrée : la réception (IMAP) et l'envoi (SMTP) répondent.")
            return redirect("courriel:comptes")
        # Nouvelle boîte : on rapatrie tout de suite ses derniers messages reçus et envoyés.
        _importer(request, boite_mail, reception=200, envoyes=100)
        return redirect(f"{reverse('courriel:boite')}?compte={boite_mail.pk}")
    return render(request, "courriel/compte.html", _barre("comptes", form=form, instance=instance, fournisseurs=FOURNISSEURS))


def _importer(request, boite_mail, reception, envoyes):
    try:
        recus, partis = protocoles.importer_historique(boite_mail, reception=reception, envoyes=envoyes)
    except protocoles.ErreurCourriel as erreur:
        CompteCourriel.objects.filter(pk=boite_mail.pk).update(derniere_erreur=str(erreur)[:300])
        messages.error(request, f"Import de {boite_mail.adresse} interrompu : {erreur}")
        return
    messages.success(request, f"{boite_mail.adresse} : {recus} message{'s' if recus > 1 else ''} reçu{'s' if recus > 1 else ''} "
                              f"et {partis} envoyé{'s' if partis > 1 else ''} importé{'s' if recus + partis > 1 else ''}.")


@equipe
@require_POST
def compte_importer(request, pk):
    """Historique plus profond : les 1 000 derniers reçus et 300 derniers envoyés (déjà importés ignorés)."""
    boite_mail = get_object_or_404(CompteCourriel, pk=pk)
    _importer(request, boite_mail, reception=1000, envoyes=300)
    return redirect("courriel:comptes")


@equipe
@require_POST
def compte_supprimer(request, pk):
    boite_mail = get_object_or_404(CompteCourriel, pk=pk)
    boite_mail.delete()
    messages.success(request, f"La boîte {boite_mail.adresse} et ses messages importés ont été retirés de l'espace. "
                              "Rien n'a été supprimé sur le serveur de messagerie.")
    return redirect("courriel:comptes")


@equipe
def piece_jointe(request, pk):
    piece = get_object_or_404(PieceJointe, pk=pk)
    # Toujours en téléchargement, jamais affichée dans le site : une pièce HTML ne peut rien y exécuter.
    return FileResponse(piece.fichier.open("rb"), as_attachment=True, filename=piece.nom)
