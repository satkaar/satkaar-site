"""Routage du site Satkaar."""

from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

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
    path("espace/agenda/", include("agenda.urls")),
    path("espace/", include("espace.urls")),
    path("", include("pages.urls")),
]
