from django.urls import path

from . import views

app_name = "courriel"

urlpatterns = [
    path("", views.boite, name="boite"),
    path("dossier/<slug:dossier>/", views.boite, name="dossier"),
    path("nouveau/", views.rediger, name="rediger"),
    path("relever/", views.relever, name="relever"),
    path("boites/", views.comptes, name="comptes"),
    path("boites/ajouter/", views.compte, name="compte_ajouter"),
    path("boites/<int:pk>/", views.compte, name="compte"),
    path("boites/<int:pk>/importer/", views.compte_importer, name="compte_importer"),
    path("boites/<int:pk>/supprimer/", views.compte_supprimer, name="compte_supprimer"),
    path("pieces/<int:pk>/", views.piece_jointe, name="piece_jointe"),
    path("<int:pk>/", views.lire, name="lire"),
    path("<int:pk>/action/", views.agir, name="agir"),
]
