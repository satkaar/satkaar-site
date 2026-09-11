from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class PagesSitemap(Sitemap):
    """Pages publiques du site, avec leur importance relative pour les moteurs."""

    PAGES = {
        "pages:accueil": (1.0, "weekly"),
        "pages:conseil": (0.9, "monthly"),
        "pages:formation": (0.9, "monthly"),
        "pages:logiciels": (0.9, "monthly"),
        "pages:isidor": (0.8, "monthly"),
        "pages:katarina": (0.8, "monthly"),
        "pages:vanessa": (0.8, "monthly"),
        "pages:bernard": (0.8, "monthly"),
        "pages:references": (0.7, "monthly"),
        "pages:a_propos": (0.7, "monthly"),
        "pages:contact": (0.7, "yearly"),
        "pages:souverainete": (0.5, "yearly"),
        "pages:mentions_legales": (0.2, "yearly"),
        "pages:confidentialite": (0.2, "yearly"),
        "pages:accessibilite": (0.2, "yearly"),
        "pages:cgu": (0.2, "yearly"),
    }

    def items(self):
        return list(self.PAGES)

    def location(self, nom):
        return reverse(nom)

    def priority(self, nom):
        return self.PAGES[nom][0]

    def changefreq(self, nom):
        return self.PAGES[nom][1]
