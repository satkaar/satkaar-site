from django.conf import settings


def adresse_client(request):
    """Adresse IP du visiteur. Derrière l'Ingress NGINX de la plateforme (PROXY_DE_CONFIANCE),
    c'est celle qu'il transmet (X-Real-IP, sinon le premier maillon de X-Forwarded-For) ;
    sinon, l'adresse de la connexion. À n'activer que derrière un proxy qui réécrit ces en-têtes."""
    if settings.PROXY_DE_CONFIANCE:
        transmise = request.META.get("HTTP_X_REAL_IP") or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0]
        if transmise.strip():
            return transmise.strip()
    return request.META.get("REMOTE_ADDR", "")
