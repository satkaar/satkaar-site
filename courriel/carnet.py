"""Carnet d'adresses de l'espace : à qui l'équipe peut écrire, et sous quel nom.

Deux sources : les fiches contact — où arrivent aussi les demandes du site, via le signal
contacts.demande_vers_lead — et les correspondants des messages déjà échangés. La fiche
donne le nom affiché ; le classement met en tête ceux avec qui on échange le plus et le
plus récemment.
"""

from email.utils import getaddresses

from contacts.models import Contact

from .models import Courriel

LIMITE_MESSAGES = 1500  # les derniers messages suffisent à connaître les correspondants
LIMITE = 400  # adresses envoyées au navigateur


def _ajouter(carnet, adresse, nom="", detail="", origine="", quand=None):
    adresse = (adresse or "").strip().lower()
    if "@" not in adresse or len(adresse) > 254:
        return None
    fiche = carnet.get(adresse)
    if fiche is None:
        fiche = carnet[adresse] = {"adresse": adresse, "nom": "", "detail": "", "origine": origine,
                                   "echanges": 0, "dernier": None}
    # Le premier passage (contacts, puis demandes) donne le nom ; les messages ne l'écrasent pas.
    if nom and not fiche["nom"]:
        fiche["nom"] = nom.strip()[:160]
    if detail and not fiche["detail"]:
        fiche["detail"] = detail.strip()[:160]
    if quand and (fiche["dernier"] is None or quand > fiche["dernier"]):
        fiche["dernier"] = quand
    return fiche


def entrees(limite=LIMITE):
    """Le carnet, prêt à être envoyé en JSON : adresse, nom, détail, origine, échanges."""
    carnet = {}

    for contact in Contact.objects.exclude(courriel="").only("nom", "courriel", "organisation", "fonction"):
        _ajouter(carnet, contact.courriel, contact.nom, contact.organisation or contact.fonction, "contact")

    messages = Courriel.objects.order_by("-date").values_list(
        "dossier", "expediteur_nom", "expediteur_adresse", "destinataires", "copie", "date")[:LIMITE_MESSAGES]
    for dossier, nom, adresse, destinataires, copie, date in messages:
        if dossier == Courriel.Dossier.ENVOYES:
            correspondants = [(n, a) for n, a in getaddresses([destinataires or "", copie or ""])]
        else:
            correspondants = [(nom, adresse)]
        for nom_vu, adresse_vue in correspondants:
            fiche = _ajouter(carnet, adresse_vue, nom_vu, origine="message", quand=date)
            if fiche:
                fiche["echanges"] += 1

    fiches = sorted(carnet.values(), key=lambda f: (-f["echanges"], -(f["dernier"].timestamp() if f["dernier"] else 0),
                                                    f["nom"].lower() or f["adresse"]))
    for fiche in fiches:
        fiche.pop("dernier")
    return fiches[:limite]
