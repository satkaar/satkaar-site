from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("conseil/", views.conseil, name="conseil"),
    path("formation/", views.formation, name="formation"),
    path("logiciels/", views.logiciels, name="logiciels"),
    path("logiciels/isidor/", views.isidor, name="isidor"),
    path("logiciels/katarina/", views.katarina, name="katarina"),
    path("logiciels/vanessa/", views.vanessa, name="vanessa"),
    path("logiciels/bernard/", views.bernard, name="bernard"),
    path("souverainete-et-conformite/", views.souverainete, name="souverainete"),
    path("references/", views.references, name="references"),
    path("a-propos/", views.a_propos, name="a_propos"),
    path("contact/", views.contact, name="contact"),
    path("contact/reformuler/", views.reformuler, name="reformuler"),
    path("mentions-legales/", views.mentions_legales, name="mentions_legales"),
    path("politique-de-confidentialite/", views.confidentialite, name="confidentialite"),
    path("declaration-d-accessibilite/", views.accessibilite, name="accessibilite"),
    path("conditions-generales-d-utilisation/", views.cgu, name="cgu"),
]
