from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("nos-solutions/", views.solutions, name="solutions"),
    path("conseil-et-accompagnement/", views.conseil, name="conseil"),
    path("souverainete-et-conformite/", views.souverainete, name="souverainete"),
    path("references/", views.references, name="references"),
    path("a-propos/", views.a_propos, name="a_propos"),
    path("contact/", views.contact, name="contact"),
    path("mentions-legales/", views.mentions_legales, name="mentions_legales"),
    path("politique-de-confidentialite/", views.confidentialite, name="confidentialite"),
    path("declaration-d-accessibilite/", views.accessibilite, name="accessibilite"),
    path("conditions-generales-d-utilisation/", views.cgu, name="cgu"),
]
