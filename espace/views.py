from django.contrib.auth import views as auth
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy

from mesure.models import Evenement

from .forms import ChangementMotDePasseForm, ConnexionForm, NouveauMotDePasseForm, ReinitialisationForm
from .models import Document, Projet


class Connexion(auth.LoginView):
    template_name = "espace/connexion.html"
    authentication_form = ConnexionForm
    redirect_authenticated_user = True


class Deconnexion(auth.LogoutView):
    next_page = reverse_lazy("pages:accueil")


@login_required
def tableau(request):
    projets = request.user.projets.all()
    return render(
        request,
        "espace/tableau.html",
        {
            "projets_actifs": projets.exclude(statut=Projet.Statut.TERMINE),
            "projets_termines": projets.filter(statut=Projet.Statut.TERMINE),
            "documents": request.user.documents.select_related("projet")[:5],
            "nb_documents": request.user.documents.count(),
        },
    )


@login_required
def documents(request):
    categorie = request.GET.get("categorie")
    liste = request.user.documents.select_related("projet")
    if categorie in Document.Categorie.values:
        liste = liste.filter(categorie=categorie)
    else:
        categorie = None
    return render(
        request,
        "espace/documents.html",
        {"documents": liste, "categories": Document.Categorie.choices, "categorie": categorie},
    )


@login_required
def telecharger(request, pk):
    # Le filtre sur le client fait qu'un document d'autrui répond « introuvable ».
    document = get_object_or_404(Document, pk=pk, client=request.user)
    Evenement.objects.create(type=Evenement.Type.TELECHARGEMENT, chemin=request.path, cible=document.get_categorie_display())
    return FileResponse(document.fichier.open("rb"), as_attachment=True, filename=document.nom_fichier)


class ChangementMotDePasse(auth.PasswordChangeView):
    template_name = "espace/mot_de_passe_changement.html"
    form_class = ChangementMotDePasseForm
    success_url = reverse_lazy("espace:mot_de_passe_change")


class MotDePasseChange(auth.PasswordChangeDoneView):
    template_name = "espace/mot_de_passe_change.html"


class Reinitialisation(auth.PasswordResetView):
    template_name = "espace/reinitialisation.html"
    form_class = ReinitialisationForm
    email_template_name = "espace/courriels/reinitialisation.txt"
    subject_template_name = "espace/courriels/reinitialisation_sujet.txt"
    success_url = reverse_lazy("espace:reinitialisation_envoyee")


class ReinitialisationEnvoyee(auth.PasswordResetDoneView):
    template_name = "espace/reinitialisation_envoyee.html"


class NouveauMotDePasse(auth.PasswordResetConfirmView):
    template_name = "espace/nouveau_mot_de_passe.html"
    form_class = NouveauMotDePasseForm
    success_url = reverse_lazy("espace:reinitialisation_terminee")


class ReinitialisationTerminee(auth.PasswordResetCompleteView):
    template_name = "espace/reinitialisation_terminee.html"
