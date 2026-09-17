"""Relève IMAP et envoi SMTP des boîtes de l'équipe, avec la seule bibliothèque standard.

- La relève lit les messages avec BODY.PEEK[] : un message ouvert ici reste « non lu » sur le
  serveur (webmail OVH, Outlook…) tant que personne ne l'y a ouvert.
- Un message envoyé est aussi déposé dans le dossier « Envoyés » du serveur, pour qu'il
  apparaisse dans les autres logiciels de messagerie.
"""

import email
import imaplib
import logging
import re
import smtplib
import ssl
from email import policy
from email.message import EmailMessage
from email.utils import formataddr, formatdate, getaddresses, make_msgid, parsedate_to_datetime

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from . import classement, redaction
from .models import CompteCourriel, Courriel, PieceJointe

logger = logging.getLogger(__name__)

DELAI = 20  # secondes, connexion et échanges
PIECE_MAX = 15 * 1024 * 1024
DOSSIERS_ENVOYES = ("Sent", "INBOX.Sent", "Envoyés", "INBOX.Envoyés", "Sent Items", "Sent Messages", "Éléments envoyés")


class ErreurCourriel(Exception):
    """Toute erreur de connexion, d'identification ou d'envoi, avec un message lisible."""


# --- Lecture d'un message ---------------------------------------------------------------------

def _entete(message, nom):
    try:
        return str(message.get(nom, "") or "").strip()
    except (ValueError, TypeError, IndexError):
        return ""


def _adresses(message, nom):
    brut = _entete(message, nom)
    return [(n, a) for n, a in getaddresses([brut]) if a] if brut else []


def _texte_partie(partie):
    try:
        return partie.get_content()
    except (LookupError, UnicodeDecodeError, AssertionError, KeyError):
        octets = partie.get_payload(decode=True) or b""
        return octets.decode("utf-8", errors="replace")


def lire_message(octets):
    """Transforme un message brut (RFC 5322) en dictionnaire prêt à enregistrer."""
    message = email.message_from_bytes(octets, policy=policy.default)
    expediteur = (_adresses(message, "From") or [("", "")])[0]
    try:
        date = parsedate_to_datetime(_entete(message, "Date"))
        if timezone.is_naive(date):
            date = timezone.make_aware(date, timezone.get_current_timezone())
    except (TypeError, ValueError, IndexError):
        date = timezone.now()

    texte = html = ""
    corps = message.get_body(preferencelist=("plain",))
    if corps is not None:
        texte = _texte_partie(corps)
    corps_html = message.get_body(preferencelist=("html",))
    if corps_html is not None:
        html = _texte_partie(corps_html)
    if not texte and html:
        # Aperçu et réponse citée : une version texte grossière du HTML.
        texte = re.sub(r"\s+", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", html, flags=re.S | re.I)).strip()

    pieces = []
    for partie in message.iter_attachments():
        contenu = partie.get_payload(decode=True) or b""
        if not contenu or len(contenu) > PIECE_MAX:
            continue
        pieces.append({
            "nom": (partie.get_filename() or "piece-jointe")[:255],
            "type_mime": partie.get_content_type()[:120],
            "contenu": contenu,
        })

    repondre_a = _adresses(message, "Reply-To")
    return {
        # Indices de classement : lettre d'information (désinscription), envoi de masse, robot.
        "entetes": {"list_unsubscribe": _entete(message, "List-Unsubscribe"),
                    "precedence": _entete(message, "Precedence"),
                    "auto_submitted": _entete(message, "Auto-Submitted")},
        "message_id": _entete(message, "Message-ID")[:512],
        "expediteur_nom": expediteur[0][:255],
        "expediteur_adresse": expediteur[1][:255],
        "destinataires": ", ".join(a for _, a in _adresses(message, "To")),
        "copie": ", ".join(a for _, a in _adresses(message, "Cc")),
        "repondre_a": repondre_a[0][1][:255] if repondre_a else "",
        "sujet": _entete(message, "Subject")[:500],
        "texte": texte,
        "html": html,
        "date": date,
        "en_reponse_a": _entete(message, "In-Reply-To")[:512],
        "references": _entete(message, "References"),
        "pieces": pieces,
    }


@transaction.atomic
def enregistrer(compte, donnees, dossier=Courriel.Dossier.RECEPTION, **champs):
    pieces = donnees.pop("pieces", [])
    donnees.pop("entetes", None)
    courriel = Courriel.objects.create(compte=compte, dossier=dossier, **donnees, **champs)
    for piece in pieces:
        PieceJointe.objects.create(
            courriel=courriel, nom=piece["nom"], type_mime=piece["type_mime"], taille=len(piece["contenu"]),
            fichier=ContentFile(piece["contenu"], name=piece["nom"]),
        )
    return courriel


# --- IMAP -------------------------------------------------------------------------------------

def _imap(compte):
    try:
        client = imaplib.IMAP4_SSL(compte.imap_hote, compte.imap_port, ssl_context=ssl.create_default_context(), timeout=DELAI)
    except (OSError, imaplib.IMAP4.error) as erreur:
        raise ErreurCourriel(f"Serveur IMAP injoignable ({compte.imap_hote}:{compte.imap_port}) : {erreur}") from erreur
    try:
        client.login(compte.identifiant, compte.mot_de_passe)
    except imaplib.IMAP4.error as erreur:
        client.shutdown()
        raise ErreurCourriel("Identifiant ou mot de passe IMAP refusé.") from erreur
    return client


def _fermer(client):
    for action in (client.close, client.logout):
        try:
            action()
        except (OSError, imaplib.IMAP4.error):
            pass


PAR_LOT = 20  # messages rapatriés par commande FETCH


def _uids_et_messages(reponse):
    """Réponse d'un FETCH groupé → [(uid, drapeaux, octets)]. L'UID et les drapeaux peuvent
    précéder ou suivre le littéral selon les serveurs."""
    resultats = []
    for i, element in enumerate(reponse or []):
        if not isinstance(element, tuple):
            continue
        entete, corps = element
        suivant = reponse[i + 1] if i + 1 < len(reponse) and isinstance(reponse[i + 1], bytes) else b""
        contexte = bytes(entete) + b" " + bytes(suivant)
        trouve = re.search(rb"UID (\d+)", contexte)
        drapeaux = re.search(rb"FLAGS \(([^)]*)\)", contexte)
        if trouve and corps:
            resultats.append((trouve.group(1).decode(), (drapeaux.group(1).decode() if drapeaux else ""), bytes(corps)))
    return resultats


def _importer_dossier(client, compte, dossier_serveur, dossier_local, limite):
    """Rapatrie les `limite` derniers messages d'un dossier du serveur, sans les marquer lus."""
    statut, _ = client.select(dossier_serveur, readonly=True)
    if statut != "OK":
        raise ErreurCourriel(f"Dossier {dossier_serveur} introuvable sur le serveur.")
    statut, donnees = client.uid("search", None, "ALL")
    uids = donnees[0].split()[-limite:] if statut == "OK" and donnees and donnees[0] else []
    connus = set(compte.courriels.filter(dossier=dossier_local).values_list("uid", flat=True))
    a_lire = [u for u in uids if u.decode() not in connus]
    nouveaux = 0
    for i in range(0, len(a_lire), PAR_LOT):
        # FLAGS : un message déjà lu dans le webmail ne doit pas ressortir « non lu » ici.
        statut, reponse = client.uid("fetch", b",".join(a_lire[i:i + PAR_LOT]), "(FLAGS BODY.PEEK[])")
        if statut != "OK":
            continue
        for uid, drapeaux, brut in _uids_et_messages(reponse):
            donnees_message = lire_message(brut)
            if not donnees_message["message_id"]:
                donnees_message["message_id"] = f"<uid-{uid}-{dossier_local}@{compte.imap_hote}>"
            existant = compte.courriels.filter(dossier=dossier_local, message_id=donnees_message["message_id"])
            if existant.exists():
                existant.update(uid=uid)  # déjà connu (envoyé d'ici, ou UIDVALIDITY changé côté serveur)
                continue
            enregistrer(compte, donnees_message, dossier=dossier_local, uid=uid,
                        lu="\\Seen" in drapeaux or dossier_local == Courriel.Dossier.ENVOYES,
                        etoile="\\Flagged" in drapeaux,
                        categorie=classement.classer(donnees_message))
            nouveaux += 1
    if dossier_local == Courriel.Dossier.RECEPTION:
        _appliquer_categories_gmail(client, compte)
    return nouveaux


def _appliquer_categories_gmail(client, compte):
    """Reprend les onglets de Gmail (Promotions, Réseaux sociaux, Notifications) sur les messages
    déjà importés. Sans effet sur les autres hébergeurs, qui gardent le classement par indices."""
    if not compte.est_gmail:
        return 0
    par_uid = classement.categories_gmail(client)
    if not par_uid:
        return 0
    connus = compte.courriels.filter(dossier=Courriel.Dossier.RECEPTION)
    modifies = 0
    for categorie in set(par_uid.values()):
        uids = [uid for uid, valeur in par_uid.items() if valeur == categorie]
        modifies += connus.filter(uid__in=uids).exclude(categorie=categorie).update(categorie=categorie)
    # Ce que Gmail ne range dans aucun onglet (sa catégorie « Personnel ») garde le classement
    # par indices : lettres d'information et réseaux sociaux y sont nombreux.
    a_classer = []
    for message in connus.exclude(uid__in=par_uid).only("id", "expediteur_adresse", "sujet", "texte", "html", "categorie"):
        categorie = classement.classer_enregistre(message)
        if message.categorie != categorie:
            message.categorie = categorie
            a_classer.append(message)
    if a_classer:
        Courriel.objects.bulk_update(a_classer, ["categorie"], batch_size=200)
        modifies += len(a_classer)
    return modifies


def reclasser(compte):
    """Relit les onglets de la boîte pour les messages déjà importés (Gmail)."""
    client = _imap(compte)
    try:
        statut, _ = client.select("INBOX", readonly=True)
        if statut != "OK":
            raise ErreurCourriel("Boîte de réception introuvable sur le serveur.")
        return _appliquer_categories_gmail(client, compte)
    except (OSError, imaplib.IMAP4.error) as erreur:
        raise ErreurCourriel(f"Classement interrompu : {erreur}") from erreur
    finally:
        _fermer(client)


def relever(compte, limite=50):
    """Importe les messages récents de la boîte de réception. Renvoie le nombre de nouveaux."""
    client = _imap(compte)
    try:
        nouveaux = _importer_dossier(client, compte, "INBOX", Courriel.Dossier.RECEPTION, limite)
    except (OSError, imaplib.IMAP4.error) as erreur:
        raise ErreurCourriel(f"Relève interrompue : {erreur}") from erreur
    finally:
        _fermer(client)
    CompteCourriel.objects.filter(pk=compte.pk).update(derniere_releve=timezone.now(), derniere_erreur="")
    return nouveaux


def importer_historique(compte, reception=200, envoyes=100):
    """Premier import d'une boîte : ses derniers messages reçus et envoyés.
    Renvoie (reçus importés, envoyés importés)."""
    client = _imap(compte)
    try:
        recus = _importer_dossier(client, compte, "INBOX", Courriel.Dossier.RECEPTION, reception)
        partis = 0
        dossier = _dossier_envoyes(client)
        if dossier and envoyes:
            partis = _importer_dossier(client, compte, dossier, Courriel.Dossier.ENVOYES, envoyes)
    except (OSError, imaplib.IMAP4.error) as erreur:
        raise ErreurCourriel(f"Import interrompu : {erreur}") from erreur
    finally:
        _fermer(client)
    CompteCourriel.objects.filter(pk=compte.pk).update(derniere_releve=timezone.now(), derniere_erreur="")
    return recus, partis


def _dossier_envoyes(client):
    """Le dossier « Envoyés » : d'abord celui marqué \\Sent (RFC 6154), sinon un nom courant."""
    statut, lignes = client.list()
    noms = []
    for ligne in (lignes if statut == "OK" and lignes else []):
        texte = ligne.decode(errors="replace") if isinstance(ligne, bytes) else str(ligne)
        correspondance = re.match(r'\((?P<drapeaux>[^)]*)\) (?:"[^"]*"|NIL) (?P<nom>.+)$', texte)
        if not correspondance:
            continue
        nom = correspondance["nom"].strip()
        if "\\Sent" in correspondance["drapeaux"]:
            return nom
        noms.append(nom.strip('"'))
    return next((f'"{n}"' for n in DOSSIERS_ENVOYES if n in noms), None)


def _deposer_dans_envoyes(compte, message):
    try:
        client = _imap(compte)
    except ErreurCourriel:
        return False
    try:
        dossier = _dossier_envoyes(client)
        if not dossier:
            return False
        statut, _ = client.append(dossier, "\\Seen", imaplib.Time2Internaldate(timezone.now()), message.as_bytes())
        return statut == "OK"
    except (OSError, imaplib.IMAP4.error, UnicodeEncodeError):
        logger.warning("Copie dans « Envoyés » impossible pour %s", compte.adresse, exc_info=True)
        return False
    finally:
        try:
            client.logout()
        except (OSError, imaplib.IMAP4.error):
            pass


# --- SMTP -------------------------------------------------------------------------------------

def _smtp(compte):
    contexte = ssl.create_default_context()
    try:
        if compte.smtp_securite == CompteCourriel.Securite.SSL:
            serveur = smtplib.SMTP_SSL(compte.smtp_hote, compte.smtp_port, context=contexte, timeout=DELAI)
        else:
            serveur = smtplib.SMTP(compte.smtp_hote, compte.smtp_port, timeout=DELAI)
            serveur.starttls(context=contexte)
    except (OSError, smtplib.SMTPException) as erreur:
        raise ErreurCourriel(f"Serveur SMTP injoignable ({compte.smtp_hote}:{compte.smtp_port}) : {erreur}") from erreur
    try:
        serveur.login(compte.identifiant, compte.mot_de_passe)
    except smtplib.SMTPException as erreur:
        serveur.close()
        raise ErreurCourriel("Identifiant ou mot de passe SMTP refusé.") from erreur
    return serveur


# OVH répartit les boîtes sur plusieurs plateformes (MX Plan, Email Pro, Exchange) que rien ne
# distingue dans le DNS du domaine : quand l'identification échoue, on essaie les autres.
SERVEURS_A_ESSAYER = [
    ("ssl0.ovh.net", "ssl0.ovh.net", 465, "ssl"),
    ("imap.mail.ovh.net", "smtp.mail.ovh.net", 465, "ssl"),
    ("pro1.mail.ovh.net", "pro1.mail.ovh.net", 587, "starttls"),
    ("pro2.mail.ovh.net", "pro2.mail.ovh.net", 587, "starttls"),
    ("pro3.mail.ovh.net", "pro3.mail.ovh.net", 587, "starttls"),
    ("ex2.mail.ovh.net", "ex2.mail.ovh.net", 587, "starttls"),
    ("ex3.mail.ovh.net", "ex3.mail.ovh.net", 587, "starttls"),
    ("ex4.mail.ovh.net", "ex4.mail.ovh.net", 587, "starttls"),
    ("ex5.mail.ovh.net", "ex5.mail.ovh.net", 587, "starttls"),
]


def detecter_serveur(compte):
    """Cherche la plateforme qui accepte ces identifiants et corrige la boîte.

    Ne s'applique qu'à OVH, dont les serveurs ne se devinent pas : ailleurs, un refus reste
    un refus. Renvoie le serveur IMAP retenu, ou None.
    """
    if "ovh" not in compte.imap_hote.lower():
        return None
    for imap_hote, smtp_hote, smtp_port, securite in SERVEURS_A_ESSAYER:
        if imap_hote == compte.imap_hote:
            continue  # déjà essayé
        essai = CompteCourriel(identifiant=compte.identifiant, mot_de_passe_chiffre=compte.mot_de_passe_chiffre,
                               imap_hote=imap_hote, imap_port=993)
        try:
            _fermer(_imap(essai))
        except ErreurCourriel:
            continue
        CompteCourriel.objects.filter(pk=compte.pk).update(
            imap_hote=imap_hote, imap_port=993, smtp_hote=smtp_hote, smtp_port=smtp_port, smtp_securite=securite)
        compte.imap_hote, compte.imap_port = imap_hote, 993
        compte.smtp_hote, compte.smtp_port, compte.smtp_securite = smtp_hote, smtp_port, securite
        logger.info("Serveur OVH détecté pour %s : %s", compte.adresse, imap_hote)
        return imap_hote
    return None


def tester(compte):
    """Vérifie IMAP puis SMTP ; lève ErreurCourriel avec la cause lisible."""
    _fermer(_imap(compte))
    serveur = _smtp(compte)
    try:
        serveur.quit()
    except smtplib.SMTPException:
        pass


def envoyer(compte, a, sujet, texte, copie=(), copie_cachee=(), pieces=(), en_reponse_a="", references="",
            utilisateur=None, html=""):
    """Envoie un message, le range dans « Envoyés » (ici et sur le serveur) et le renvoie.

    Avec `html`, le message part en deux versions : le texte pour les logiciels qui n'affichent
    pas le HTML, la mise en forme pour les autres.
    """
    message = EmailMessage(policy=policy.SMTP)
    message["From"] = formataddr((compte.nom_expediteur, compte.adresse))
    message["To"] = ", ".join(a)
    if copie:
        message["Cc"] = ", ".join(copie)
    message["Subject"] = sujet
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain=compte.adresse.rpartition("@")[2] or None)
    if en_reponse_a:
        message["In-Reply-To"] = en_reponse_a
        message["References"] = f"{references} {en_reponse_a}".strip()
    html = redaction.nettoyer(html)
    message.set_content(texte)
    if html:
        message.add_alternative(html, subtype="html")
    for piece in pieces:
        principal, _, secondaire = piece["type_mime"].partition("/")
        message.add_attachment(piece["contenu"], maintype=principal or "application",
                               subtype=secondaire or "octet-stream", filename=piece["nom"])

    serveur = _smtp(compte)
    try:
        serveur.send_message(message, to_addrs=[*a, *copie, *copie_cachee])
    except (OSError, smtplib.SMTPException) as erreur:
        raise ErreurCourriel(f"Envoi refusé par le serveur : {erreur}") from erreur
    finally:
        try:
            serveur.quit()
        except (OSError, smtplib.SMTPException):
            pass

    if not compte.copie_envoyes_automatique:
        _deposer_dans_envoyes(compte, message)
    return enregistrer(
        compte,
        {
            "message_id": message["Message-ID"], "expediteur_nom": compte.nom_expediteur,
            "expediteur_adresse": compte.adresse, "destinataires": ", ".join(a), "copie": ", ".join(copie),
            "sujet": sujet, "texte": texte, "html": html, "date": timezone.now(), "en_reponse_a": en_reponse_a,
            "references": message.get("References", ""), "pieces": list(pieces),
        },
        dossier=Courriel.Dossier.ENVOYES, lu=True, envoye_par=utilisateur,
    )
