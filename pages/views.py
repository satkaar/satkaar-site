from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import DemandeDemonstrationForm


def _page(gabarit):
    """Vue de contenu statique : le texte vit dans le gabarit."""

    def vue(request):
        return render(request, gabarit)

    return vue


accueil = _page("pages/accueil.html")
solutions = _page("pages/solutions.html")
conseil = _page("pages/conseil.html")
souverainete = _page("pages/souverainete.html")
references = _page("pages/references.html")
a_propos = _page("pages/a_propos.html")

mentions_legales = _page("legal/mentions_legales.html")
confidentialite = _page("legal/confidentialite.html")
accessibilite = _page("legal/accessibilite.html")
cgu = _page("legal/cgu.html")


def contact(request):
    if request.method == "POST":
        form = DemandeDemonstrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('pages:contact')}?envoye=1")
    else:
        form = DemandeDemonstrationForm()

    return render(
        request,
        "pages/contact.html",
        {"form": form, "envoye": request.GET.get("envoye") == "1"},
    )
