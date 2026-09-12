from django.urls import path

from . import views

app_name = "agenda"

urlpatterns = [
    path("", views.semaine, name="semaine"),
    path("semaine/<int:annee>/<int:mois>/<int:jour>/", views.semaine, name="semaine_du"),
    path("mois/", views.mois, name="mois"),
    path("mois/<int:annee>/<int:mois>/", views.mois, name="mois_de"),
    path("nouveau/", views.editer, name="ajouter"),
    path("<int:pk>/", views.evenement, name="evenement"),
    path("<int:pk>/modifier/", views.editer, name="modifier"),
    path("<int:pk>/supprimer/", views.supprimer, name="supprimer"),
    path("<int:pk>/agenda.ics", views.ics, name="ics"),
]
