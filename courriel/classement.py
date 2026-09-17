"""Classement des messages entrants en quatre onglets, comme Gmail.

Deux sources, dans cet ordre :
1. Gmail donne ses propres catégories (recherche IMAP `X-GM-RAW category:…`) : ses onglets
   sont alors repris à l'identique, pour ne pas dérouter qui connaît déjà sa boîte.
2. Les autres boîtes (OVH…) sont classées d'après les indices du message : domaine de
   l'expéditeur, en-têtes de désinscription, mots du sujet.
"""

import re

from .models import Courriel

# Catégories Gmail → onglets. « Forums » rejoint les notifications : les listes de discussion
# relèvent du même geste de lecture, et un cinquième onglet chargerait la barre pour rien.
CATEGORIES_GMAIL = {
    "promotions": Courriel.Categorie.PROMOTIONS,
    "social": Courriel.Categorie.RESEAUX,
    "updates": Courriel.Categorie.NOTIFICATIONS,
    "forums": Courriel.Categorie.NOTIFICATIONS,
}

RESEAUX = ("linkedin.com", "facebookmail.com", "facebook.com", "instagram.com", "x.com", "twitter.com",
           "pinterest.com", "tiktok.com", "youtube.com", "snapchat.com", "meetup.com", "viadeo.com",
           "mastodon.social", "bsky.app", "threads.net")

# Expéditeurs automatiques : confirmations, alertes, factures…
EXPEDITEURS_AUTOMATIQUES = ("noreply", "no-reply", "nepasrepondre", "ne-pas-repondre", "donotreply",
                            "notification", "notifications", "alerte", "alertes", "alert", "security",
                            "securite", "facture", "billing", "invoice", "support", "service-client")
MOTS_NOTIFICATION = ("facture", "commande", "confirmation", "reçu", "recu", "alerte", "sécurité", "securite",
                     "mot de passe", "connexion", "livraison", "rendez-vous", "abonnement", "paiement",
                     "relevé", "releve", "ticket", "mise à jour", "mise a jour")
MOTS_PROMOTION = ("promo", "soldes", "offre", "offres", "réduction", "reduction", "remise", "newsletter",
                  "nouveauté", "nouveautes", "nouveautés", "black friday", "vente privée", "vente privee",
                  "code promo", "livraison offerte", "% de remise", "profitez", "dernière chance",
                  "derniere chance", "webinar", "webinaire", "inscrivez-vous")


def _domaine(adresse):
    return (adresse or "").rsplit("@", 1)[-1].lower()


# Mots d'un lien de désinscription : à défaut d'en-tête (messages déjà importés), ils
# trahissent tout aussi sûrement un envoi de masse.
MOTS_DESINSCRIPTION = ("désinscri", "desinscri", "unsubscribe", "se désabonner", "se desabonner",
                       "ne plus recevoir", "gérer mes préférences", "list-unsubscribe")


def classer(donnees):
    """Catégorie d'un message d'après son expéditeur, ses en-têtes et son sujet.

    `donnees` est le dictionnaire produit par `protocoles.lire_message`, ou un dictionnaire
    équivalent reconstruit depuis un message déjà enregistré.
    """
    domaine = _domaine(donnees.get("expediteur_adresse"))
    local = (donnees.get("expediteur_adresse") or "").split("@")[0].lower()
    sujet = (donnees.get("sujet") or "").lower()
    entetes = donnees.get("entetes") or {}
    corps = ((donnees.get("texte") or "") + " " + (donnees.get("html") or "")).lower()
    desinscription = bool(entetes.get("list_unsubscribe")) or any(m in corps for m in MOTS_DESINSCRIPTION)
    automatique = (entetes.get("auto_submitted") or "").lower() not in ("", "no")
    en_masse = (entetes.get("precedence") or "").lower() in ("bulk", "list", "junk")

    if any(domaine == r or domaine.endswith("." + r) for r in RESEAUX):
        return Courriel.Categorie.RESEAUX
    if any(mot in sujet for mot in MOTS_PROMOTION) and (desinscription or en_masse):
        return Courriel.Categorie.PROMOTIONS
    if automatique or any(local.startswith(a) for a in EXPEDITEURS_AUTOMATIQUES) \
            or any(mot in sujet for mot in MOTS_NOTIFICATION):
        return Courriel.Categorie.NOTIFICATIONS
    if desinscription or en_masse:
        # Un envoi de masse sans marqueur transactionnel : une communication commerciale.
        return Courriel.Categorie.PROMOTIONS
    return Courriel.Categorie.PRINCIPALE


def classer_enregistre(courriel):
    """Catégorie d'un message déjà en base : ses en-têtes ne sont plus là, on lit son contenu.

    Le lien de désinscription vit en pied de message : on regarde donc aussi la fin du HTML,
    sans charger des mégaoctets d'images encodées.
    """
    html, texte = courriel.html or "", courriel.texte or ""
    return classer({"expediteur_adresse": courriel.expediteur_adresse, "sujet": courriel.sujet,
                    "texte": texte[:8000] + " " + texte[-8000:],
                    "html": html[:4000] + " " + html[-8000:]})


def categories_gmail(client, uids=None):
    """{uid: catégorie} d'après les onglets de Gmail eux-mêmes (extension X-GM-RAW).

    Renvoie un dictionnaire vide si le serveur ne connaît pas l'extension.
    """
    trouvees = {}
    connus = {u.decode() if isinstance(u, bytes) else str(u) for u in (uids or [])}
    for nom, categorie in CATEGORIES_GMAIL.items():
        try:
            statut, donnees = client.uid("search", None, "X-GM-RAW", f'"category:{nom}"')
        except Exception:  # extension absente : on garde le classement par indices  # noqa: BLE001
            return {}
        if statut != "OK" or not donnees or not donnees[0]:
            continue
        for uid in donnees[0].split():
            uid = uid.decode()
            if not connus or uid in connus:
                trouvees[uid] = categorie
    return trouvees


def onglets(messages):
    """Compteurs et aperçu de chaque onglet, pour la barre de la boîte de réception."""
    resultat = []
    for cle, libelle in Courriel.Categorie.choices:
        du_groupe = [m for m in messages if m.categorie == cle]
        dernier = du_groupe[0] if du_groupe else None
        resultat.append({
            "cle": cle, "libelle": libelle, "total": len(du_groupe),
            "nouveaux": sum(1 for m in du_groupe if not m.lu),
            "apercu": f"{dernier.correspondant} — {dernier.sujet or '(sans objet)'}"[:70] if dernier else "",
        })
    return resultat


def nettoyer_sujet(sujet):
    """Sujet sans les préfixes de réponse, pour comparer deux messages d'un même fil."""
    return re.sub(r"^((re|tr|fw|fwd)\s*:\s*)+", "", (sujet or "").strip(), flags=re.I)
