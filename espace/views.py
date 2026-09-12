from django.contrib.auth import views as auth
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse_lazy

from .forms import ChangementMotDePasseForm, ConnexionForm, NouveauMotDePasseForm, ReinitialisationForm
from .models import Projet


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
        },
    )


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
