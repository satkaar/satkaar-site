"""Santé technique du site : chaque page du plan du site est chargée et contrôlée.

Le résultat est gardé une heure en cache : l'audit charge toutes les pages publiques.
"""

import re
import time

from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from pages.sitemaps import PagesSitemap

from .middleware import AUDIT_INTERNE

CLE_CACHE = "mesure:sante"


def auditer(hote, forcer=False):
    if not forcer:
        resultat = cache.get(CLE_CACHE)
        if resultat:
            return resultat

    client = Client(HTTP_HOST=hote, HTTP_USER_AGENT=AUDIT_INTERNE)
    pages, liens = [], set()
    for nom in PagesSitemap.PAGES:
        chemin = reverse(nom)
        debut = time.perf_counter()
        reponse = client.get(chemin)
        duree = round((time.perf_counter() - debut) * 1000)
        html = reponse.content.decode("utf-8", "replace")
        titre = (re.search(r"<title>(.*?)</title>", html, re.S) or [None, ""])[1].strip()
        description = (re.search(r'<meta name="description" content="([^"]*)"', html) or [None, ""])[1]
        liens.update(re.findall(r'href="(/[^"#?]*)', html))
        pages.append({
            "chemin": chemin,
            "titre": titre,
            "statut": reponse.status_code,
            "duree_ms": duree,
            "poids_ko": round(len(reponse.content) / 1024, 1),
            "titre_ok": 20 <= len(titre) <= 65,
            "description_ok": 70 <= len(description) <= 160,
            "h1_ok": len(re.findall(r"<h1[ >]", html)) == 1,
            "jsonld": len(re.findall(r'application/ld\+json', html)),
            "canonique": 'rel="canonical"' in html,
            "images_sans_alt": len(re.findall(r"<img(?![^>]*\balt=)[^>]*>", html)),
            "indexable": "noindex" not in html,
        })

    # Liens internes cassés (fichiers statiques exclus : ils sont servis à part).
    casses = []
    for lien in sorted(liens):
        if lien.startswith(("/static/", "/media/", "/espace/", "/admin/")):
            continue
        if client.get(lien).status_code >= 400:
            casses.append(lien)

    n = len(pages)
    resultat = {
        "pages": pages,
        "nb_pages": n,
        "titres_ok": sum(p["titre_ok"] for p in pages),
        "descriptions_ok": sum(p["description_ok"] for p in pages),
        "h1_ok": sum(p["h1_ok"] for p in pages),
        "avec_jsonld": sum(1 for p in pages if p["jsonld"]),
        "canoniques": sum(p["canonique"] for p in pages),
        "indexables": sum(p["indexable"] for p in pages),
        "images_sans_alt": sum(p["images_sans_alt"] for p in pages),
        "poids_moyen_ko": round(sum(p["poids_ko"] for p in pages) / n, 1) if n else 0,
        "duree_moyenne_ms": round(sum(p["duree_ms"] for p in pages) / n) if n else 0,
        "liens_verifies": len(liens),
        "liens_casses": casses,
        "titres": {p["chemin"]: p["titre"].split(" | ")[0].split(" — ")[0] for p in pages},
    }
    cache.set(CLE_CACHE, resultat, 3600)
    return resultat
