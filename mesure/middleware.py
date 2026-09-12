import time

from . import detection
from .models import PageVue, PassageRobot

# Rien n'est mesuré sur ces adresses (administration, espace privé, fichiers, collecte).
EXCLUS = ("/admin/", "/espace/", "/static/", "/media/", "/mesure/", "/contact/reformuler/", "/favicon")
# Fichiers lus par les robots : leurs passages y sont comptés, mais ce ne sont pas des pages vues.
FICHIERS_ROBOTS = ("/robots.txt", "/llms.txt", "/sitemap.xml")
AUDIT_INTERNE = "SatkaarAudit"


class MesureAudienceMiddleware:
    """Enregistre les pages vues des visiteurs et les passages des robots."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        debut = time.perf_counter()
        reponse = self.get_response(request)
        try:
            self._enregistrer(request, reponse, int((time.perf_counter() - debut) * 1000))
        except Exception:  # la mesure ne doit jamais casser une page
            pass
        return reponse

    def _enregistrer(self, request, reponse, duree_ms):
        chemin = request.path
        ua = request.META.get("HTTP_USER_AGENT", "")
        if request.method != "GET" or chemin.startswith(EXCLUS) or AUDIT_INTERNE in ua:
            return

        est_robot = detection.robot(ua)
        if est_robot:
            nom, famille = est_robot
            PassageRobot.objects.create(robot=nom, famille=famille, chemin=chemin[:300])
            return

        if chemin in FICHIERS_ROBOTS or reponse.status_code not in (200, 404):
            return
        if "text/html" not in reponse.get("Content-Type", ""):
            return
        # Préchargements du navigateur, équipe Satkaar et refus du suivi : non comptés.
        if request.META.get("HTTP_SEC_PURPOSE", "").startswith("prefetch") or request.META.get("HTTP_PURPOSE") == "prefetch":
            return
        if getattr(request, "user", None) is not None and request.user.is_authenticated and request.user.is_staff:
            return
        if detection.refuse_le_suivi(request):
            return

        utm = request.GET
        source, referent = detection.source(
            request.META.get("HTTP_REFERER", ""), request.get_host(), utm.get("utm_source", "")
        )
        PageVue.objects.create(
            chemin=chemin[:300],
            statut=reponse.status_code,
            visiteur=detection.empreinte(request),
            source=source,
            referent=referent[:120],
            utm_source=utm.get("utm_source", "")[:80],
            utm_medium=utm.get("utm_medium", "")[:80],
            utm_campagne=utm.get("utm_campaign", "")[:80],
            appareil=detection.appareil(ua),
            navigateur=detection.navigateur(ua),
            systeme=detection.systeme(ua),
            langue=detection.langue(request.META.get("HTTP_ACCEPT_LANGUAGE", "")),
            duree_serveur_ms=duree_ms,
        )
