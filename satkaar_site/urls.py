from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from vitrine.sitemaps import StaticSitemap

sitemaps = {"static": StaticSitemap}

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("", include("vitrine.urls")),
]
