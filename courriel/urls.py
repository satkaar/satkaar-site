from django.urls import path

from . import views

app_name = "courriel"

urlpatterns = [
    path("", views.boite, name="boite"),
    path("dossier/<slug:dossier>/", views.boite, name="dossier"),
    path("nouveau/", views.rediger, name="rediger"),
    path("relever/", views.relever, name="relever"),
    path("carnet/", views.carnet_adresses, name="carnet"),
    path("modeles/", views.modeles, name="modeles"),
    path("modeles/ajouter/", views.modele, name="modele_ajouter"),
    path("modeles/depuis-message/", views.modele_depuis_message, name="modele_depuis_message"),
    path("modeles/<int:pk>/", views.modele, name="modele"),
    path("modeles/<int:pk>/supprimer/", views.modele_supprimer, name="modele_supprimer"),
    path("signatures/", views.signatures, name="signatures"),
    path("signatures/ajouter/", views.signature, name="signature_ajouter"),
    path("signatures/<int:pk>/", views.signature, name="signature"),
    path("signatures/<int:pk>/supprimer/", views.signature_supprimer, name="signature_supprimer"),
    path("objet/", views.objet_ia, name="objet_ia"),
    path("reformuler/", views.reformuler, name="reformuler"),
    path("boites/", views.comptes, name="comptes"),
    path("boites/ajouter/", views.compte, name="compte_ajouter"),
    path("boites/<int:pk>/", views.compte, name="compte"),
    path("boites/<int:pk>/importer/", views.compte_importer, name="compte_importer"),
    path("boites/<int:pk>/supprimer/", views.compte_supprimer, name="compte_supprimer"),
    path("pieces/<int:pk>/", views.piece_jointe, name="piece_jointe"),
    path("<int:pk>/", views.lire, name="lire"),
    path("<int:pk>/action/", views.agir, name="agir"),
]
