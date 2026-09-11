from django.urls import path

from . import views

app_name = "espace"

urlpatterns = [
    path("", views.tableau, name="tableau"),
    path("documents/", views.documents, name="documents"),
    path("documents/<int:pk>/telecharger/", views.telecharger, name="telecharger"),
    path("connexion/", views.Connexion.as_view(), name="connexion"),
    path("deconnexion/", views.Deconnexion.as_view(), name="deconnexion"),
    path("mot-de-passe/", views.ChangementMotDePasse.as_view(), name="mot_de_passe"),
    path("mot-de-passe/modifie/", views.MotDePasseChange.as_view(), name="mot_de_passe_change"),
    path("mot-de-passe-oublie/", views.Reinitialisation.as_view(), name="reinitialisation"),
    path("mot-de-passe-oublie/envoye/", views.ReinitialisationEnvoyee.as_view(), name="reinitialisation_envoyee"),
    path("reinitialiser/<uidb64>/<token>/", views.NouveauMotDePasse.as_view(), name="nouveau_mot_de_passe"),
    path("reinitialiser/termine/", views.ReinitialisationTerminee.as_view(), name="reinitialisation_terminee"),
]
