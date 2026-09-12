from django.conf import settings


def pas_d_indexation(get_response):
    """Préproduction : aucune page ne doit apparaître dans les moteurs de recherche."""

    def middleware(request):
        reponse = get_response(request)
        if settings.NOINDEX:
            reponse["X-Robots-Tag"] = "noindex, nofollow"
        return reponse

    return middleware
