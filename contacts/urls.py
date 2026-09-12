from django.urls import path

from . import views

app_name = "contacts"

urlpatterns = [
    path("", views.liste, name="liste"),
    path("nouveau/", views.editer, name="ajouter"),
    path("export.csv", views.export, name="export"),
    path("<int:pk>/", views.fiche, name="fiche"),
    path("<int:pk>/modifier/", views.editer, name="modifier"),
    path("<int:pk>/etape/", views.changer_etape, name="etape"),
    path("<int:pk>/echanges/", views.ajouter_note, name="note"),
    path("<int:pk>/supprimer/", views.supprimer, name="supprimer"),
]
