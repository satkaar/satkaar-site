"""Routage du site Satkaar."""

from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.generic import RedirectView

from mesure import views as mesure_views
from pages import views as pages_views
from pages.sitemaps import PagesSitemap

urlpatterns = [
    path("admin/", admin.site.urls),
    path("robots.txt", pages_views.robots, name="robots"),
    path("llms.txt", pages_views.llms, name="llms"),
    path("mesure/", mesure_views.collecte, name="mesure"),
    path("sitemap.xml", sitemap, {"sitemaps": {"pages": PagesSitemap}}, name="sitemap"),
    path("espace/mail/", include("courriel.urls")),
    # Ancienne adresse du Mail (« Courriels ») : les favoris et liens déjà envoyés restent valables.
    re_path(r"^espace/courriels/(?P<reste>.*)$", RedirectView.as_view(url="/espace/mail/%(reste)s", permanent=True, query_string=True)),
    path("espace/agenda/", include("agenda.urls")),
    path("espace/contacts/", include("contacts.urls")),
    path("espace/", include("espace.urls")),
    path("", include("pages.urls")),
]
