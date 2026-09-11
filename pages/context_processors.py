from . import seo


def referencement(request):
    """Adresse canonique et fiche schema.org de l'organisation, pour chaque page."""
    return {
        "url_canonique": request.build_absolute_uri(request.path),
        "jsonld_organisation": seo.organisation(request),
    }
