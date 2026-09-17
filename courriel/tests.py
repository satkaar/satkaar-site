import imaplib
import shutil
import tempfile
from email import policy
from email.message import EmailMessage
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from . import protocoles
from .models import CompteCourriel, Courriel, PieceJointe
from .views import _document_isole


def message_brut(sujet="Demande de devis", message_id="<a1@client.fr>", avec_piece=True):
    message = EmailMessage(policy=policy.SMTP)
    message["From"] = "Élodie Martin <elodie@client.fr>"
    message["To"] = "contact@satkaar.io, autre@satkaar.io"
    message["Cc"] = "copie@client.fr"
    message["Subject"] = sujet
    message["Date"] = "Thu, 10 Sep 2026 09:30:00 +0200"
    message["Message-ID"] = message_id
    message.set_content("Bonjour,\nPouvez-vous nous rappeler ?\nÉlodie")
    message.add_alternative("<p>Bonjour,</p><p>Pouvez-vous nous <b>rappeler</b> ?</p><img src='https://pisteur.fr/o.gif'>", subtype="html")
    if avec_piece:
        message.add_attachment(b"%PDF-1.4 cahier", maintype="application", subtype="pdf", filename="cahier des charges.pdf")
    return message.as_bytes()


class FauxIMAP:
    def __init__(self, messages, envoyes=None, drapeaux=None, categories=None):
        self.dossiers = {"INBOX": messages, '"INBOX.Sent"': envoyes or {}}
        self.messages = messages
        self.drapeaux = drapeaux or {}
        self.categories = categories or {}
        self.commandes = []
        self.lecture_seule = None
        self.depose = None

    def login(self, identifiant, mot_de_passe):
        if mot_de_passe != "secret":
            raise imaplib.IMAP4.error("AUTHENTICATIONFAILED")

    def select(self, dossier, readonly=False):
        self.lecture_seule = readonly
        self.messages = self.dossiers[dossier]
        return "OK", [str(len(self.messages)).encode()]

    def uid(self, commande, *arguments):
        self.commandes.append((commande, *arguments))
        if commande == "search":
            if "X-GM-RAW" in arguments:  # recherche par onglet Gmail
                nom = arguments[-1].strip('"').split(":")[-1]
                return "OK", [b" ".join(self.categories.get(nom, []))]
            return "OK", [b" ".join(self.messages)]
        uids, parties = arguments
        reponse = []
        for uid in uids.split(b","):
            drapeaux = self.drapeaux.get(uid, b"")
            reponse += [(b"1 (UID " + uid + b" FLAGS (" + drapeaux + b") BODY[] {100}", self.messages[uid]), b")"]
        return "OK", reponse

    def list(self):
        return "OK", [b'(\\HasNoChildren) "." "INBOX"', b'(\\HasNoChildren \\Sent) "." "INBOX.Sent"']

    def append(self, dossier, drapeaux, date, octets):
        self.depose = (dossier, drapeaux, octets)
        return "OK", [b"APPEND completed"]

    def close(self):
        pass

    def logout(self):
        pass

    def shutdown(self):
        pass


class FauxSMTP:
    envois = []

    def __init__(self, *args, **kwargs):
        pass

    def login(self, identifiant, mot_de_passe):
        pass

    def starttls(self, **kwargs):
        pass

    def send_message(self, message, to_addrs):
        FauxSMTP.envois.append((message, to_addrs))

    def quit(self):
        pass

    def close(self):
        pass


class Base(TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        reglage = override_settings(ESPACE_DOCUMENTS_ROOT=Path(self.dossier))
        reglage.enable()
        self.addCleanup(reglage.disable)
        self.addCleanup(shutil.rmtree, self.dossier, ignore_errors=True)
        self.compte = CompteCourriel(adresse="contact@satkaar.io", identifiant="contact@satkaar.io",
                                     imap_hote="ssl0.ovh.net", smtp_hote="ssl0.ovh.net", signature="Damien — Satkaar")
        self.compte.mot_de_passe = "secret"
        self.compte.save()
        FauxSMTP.envois = []


class ChiffrementTests(Base):
    def test_mot_de_passe_chiffre_en_base(self):
        brut = bytes(CompteCourriel.objects.get().mot_de_passe_chiffre)
        self.assertNotIn(b"secret", brut)
        self.assertEqual(CompteCourriel.objects.get().mot_de_passe, "secret")


class LectureTests(Base):
    def test_message_multipart(self):
        donnees = protocoles.lire_message(message_brut())
        self.assertEqual(donnees["expediteur_nom"], "Élodie Martin")
        self.assertEqual(donnees["expediteur_adresse"], "elodie@client.fr")
        self.assertEqual(donnees["destinataires"], "contact@satkaar.io, autre@satkaar.io")
        self.assertEqual(donnees["copie"], "copie@client.fr")
        self.assertIn("Pouvez-vous nous rappeler", donnees["texte"])
        self.assertIn("<b>rappeler</b>", donnees["html"])
        self.assertEqual(donnees["date"].isoformat(), "2026-09-10T09:30:00+02:00")
        self.assertEqual([p["nom"] for p in donnees["pieces"]], ["cahier des charges.pdf"])

    def test_html_seul_donne_un_apercu_texte(self):
        message = EmailMessage()
        message["Subject"] = "Lettre"
        message.set_content("<html><style>p{}</style><p>Nouvelle offre</p></html>", subtype="html")
        self.assertEqual(protocoles.lire_message(message.as_bytes())["texte"], "Nouvelle offre")


class ReleveTests(Base):
    def test_releve_sans_marquer_lu_et_sans_doublon(self):
        faux = FauxIMAP({b"7": message_brut(), b"8": message_brut("Relance", "<a2@client.fr>", avec_piece=False)})
        with mock.patch("courriel.protocoles.imaplib.IMAP4_SSL", return_value=faux):
            self.assertEqual(protocoles.relever(self.compte), 2)
            self.assertEqual(protocoles.relever(self.compte), 0)
        self.assertTrue(faux.lecture_seule)
        # PEEK : lire un message ici ne le marque pas comme lu sur le serveur.
        self.assertTrue(all("BODY.PEEK[]" in c[2] and "BODY[]" not in c[2].replace("BODY.PEEK[]", "")
                            for c in faux.commandes if c[0] == "fetch"))
        self.assertEqual(Courriel.objects.count(), 2)
        piece = PieceJointe.objects.get()
        self.assertEqual(piece.taille, len(b"%PDF-1.4 cahier"))
        self.compte.refresh_from_db()
        self.assertIsNotNone(self.compte.derniere_releve)

    def test_mot_de_passe_refuse(self):
        self.compte.mot_de_passe = "faux"
        with mock.patch("courriel.protocoles.imaplib.IMAP4_SSL", return_value=FauxIMAP({})):
            with self.assertRaisesMessage(protocoles.ErreurCourriel, "refusé"):
                protocoles.relever(self.compte)


class ImportTests(Base):
    def test_historique_recus_et_envoyes(self):
        envoye = message_brut("Re: Demande de devis", "<envoi-1@satkaar.io>", avec_piece=False)
        faux = FauxIMAP({b"7": message_brut(), b"8": message_brut("Relance", "<a2@client.fr>", avec_piece=False)},
                        envoyes={b"3": envoye})
        with mock.patch("courriel.protocoles.imaplib.IMAP4_SSL", return_value=faux):
            self.assertEqual(protocoles.importer_historique(self.compte), (2, 1))
            self.assertEqual(protocoles.importer_historique(self.compte), (0, 0))
        envoi = Courriel.objects.get(dossier=Courriel.Dossier.ENVOYES)
        self.assertTrue(envoi.lu)
        self.assertEqual(envoi.sujet, "Re: Demande de devis")
        # Un seul FETCH groupé pour les deux messages reçus.
        self.assertEqual([c[1] for c in faux.commandes if c[0] == "fetch"][0], b"7,8")

    def test_uid_apres_le_litteral(self):
        reponse = [(b"1 (BODY[] {5}", b"12345"), b" UID 42 FLAGS (\\Seen))"]
        self.assertEqual(protocoles._uids_et_messages(reponse), [("42", "\\Seen", b"12345")])

    def test_messages_deja_lus_sur_le_serveur(self):
        """Un message lu (ou marqué) dans le webmail arrive lu (ou étoilé) ici."""
        faux = FauxIMAP({b"7": message_brut(), b"8": message_brut("Relance", "<a2@client.fr>", avec_piece=False)},
                        drapeaux={b"7": b"\\Seen", b"8": b"\\Flagged"})
        with mock.patch("courriel.protocoles.imaplib.IMAP4_SSL", return_value=faux):
            protocoles.relever(self.compte)
        lu = Courriel.objects.get(uid="7")
        non_lu = Courriel.objects.get(uid="8")
        self.assertTrue(lu.lu)
        self.assertFalse(lu.etoile)
        self.assertFalse(non_lu.lu)
        self.assertTrue(non_lu.etoile)


class GmailTests(Base):
    def setUp(self):
        super().setUp()
        self.gmail = CompteCourriel(adresse="damien@gmail.com", identifiant="damien@gmail.com",
                                    imap_hote="imap.gmail.com", smtp_hote="smtp.gmail.com")
        self.gmail.mot_de_passe = "secret"
        self.gmail.save()

    def test_pas_de_seconde_copie_dans_envoyes(self):
        faux = FauxIMAP({})
        with mock.patch("courriel.protocoles.smtplib.SMTP_SSL", FauxSMTP), \
                mock.patch("courriel.protocoles.imaplib.IMAP4_SSL", return_value=faux):
            protocoles.envoyer(self.gmail, ["elodie@client.fr"], "Bonjour", "Texte")
        self.assertEqual(len(FauxSMTP.envois), 1)
        self.assertIsNone(faux.depose)  # Gmail range lui-même le message dans « Envoyés »
        self.assertTrue(self.gmail.est_gmail)
        self.assertFalse(self.compte.copie_envoyes_automatique)

    def test_mot_de_passe_d_application_avec_espaces(self):
        from .forms import CompteForm

        form = CompteForm({"adresse": "autre@gmail.com", "nom_expediteur": "Satkaar", "identifiant": "autre@gmail.com",
                           "mot_de_passe": "abcd efgh ijkl mnop", "imap_hote": "imap.gmail.com", "imap_port": 993,
                           "smtp_hote": "smtp.gmail.com", "smtp_port": 465, "smtp_securite": "ssl", "actif": "on"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().mot_de_passe, "abcdefghijklmnop")


class EnvoiTests(Base):
    def test_envoi_cci_reponse_et_copie_dans_envoyes(self):
        faux = FauxIMAP({})
        with mock.patch("courriel.protocoles.smtplib.SMTP_SSL", FauxSMTP), \
                mock.patch("courriel.protocoles.imaplib.IMAP4_SSL", return_value=faux):
            envoye = protocoles.envoyer(
                self.compte, ["elodie@client.fr"], "Re: Demande", "Bonjour Élodie", copie=["copie@client.fr"],
                copie_cachee=["archive@satkaar.io"], en_reponse_a="<a1@client.fr>",
                pieces=[{"nom": "devis.pdf", "type_mime": "application/pdf", "contenu": b"%PDF devis"}],
            )
        message, destinataires = FauxSMTP.envois[0]
        self.assertEqual(destinataires, ["elodie@client.fr", "copie@client.fr", "archive@satkaar.io"])
        self.assertIsNone(message["Bcc"])
        self.assertEqual(message["In-Reply-To"], "<a1@client.fr>")
        self.assertEqual(message["From"], "Satkaar <contact@satkaar.io>")
        self.assertEqual(faux.depose[0], '"INBOX.Sent"')
        self.assertEqual(envoye.dossier, Courriel.Dossier.ENVOYES)
        self.assertEqual(envoye.pieces_jointes.get().nom, "devis.pdf")


class VuesTests(Base):
    def setUp(self):
        super().setUp()
        utilisateurs = get_user_model().objects
        self.equipe = utilisateurs.create_user("equipe", "equipe@satkaar.io", "x", is_staff=True)
        self.client_site = utilisateurs.create_user("client", "client@mairie.fr", "x")
        self.recu = protocoles.enregistrer(self.compte, protocoles.lire_message(message_brut()), uid="7")

    def test_reserve_a_l_equipe(self):
        self.assertEqual(self.client.get(reverse("courriel:boite")).status_code, 302)
        self.client.force_login(self.client_site)
        for url in (reverse("courriel:boite"), reverse("courriel:lire", args=[self.recu.pk]),
                    reverse("courriel:piece_jointe", args=[self.recu.pieces_jointes.get().pk])):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_liste_et_lecture(self):
        self.client.force_login(self.equipe)
        with mock.patch("courriel.views.protocoles.relever"):
            reponse = self.client.get(reverse("courriel:boite"))
        self.assertContains(reponse, "Demande de devis")
        self.assertContains(reponse, "courriel-ligne--non-lu")
        reponse = self.client.get(reverse("courriel:lire", args=[self.recu.pk]))
        self.assertContains(reponse, 'sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"')
        self.assertNotContains(reponse, "allow-scripts")
        self.assertContains(reponse, "Afficher les images")
        self.recu.refresh_from_db()
        self.assertTrue(self.recu.lu)

    def test_images_distantes_bloquees_par_defaut(self):
        self.assertIn('img-src data: cid:"', _document_isole("<p>x</p>", images=False))
        self.assertIn("https:", _document_isole("<p>x</p>", images=True))

    def test_action_et_redirection_sure(self):
        self.client.force_login(self.equipe)
        reponse = self.client.post(reverse("courriel:agir", args=[self.recu.pk]),
                                   {"action": "etoile", "suivant": "https://pirate.example/"})
        self.assertRedirects(reponse, reverse("courriel:boite"), fetch_redirect_response=False)
        self.recu.refresh_from_db()
        self.assertTrue(self.recu.etoile)

    def test_reponse_preremplie(self):
        self.client.force_login(self.equipe)
        reponse = self.client.get(reverse("courriel:rediger"), {"mode": "repondre_tous", "origine": self.recu.pk})
        formulaire = reponse.context["form"]
        self.assertEqual(formulaire.initial["a"], "elodie@client.fr")
        self.assertEqual(formulaire.initial["copie"], "autre@satkaar.io, copie@client.fr")
        self.assertEqual(formulaire.initial["sujet"], "Re: Demande de devis")
        self.assertIn("-- \nDamien — Satkaar", formulaire.initial["texte"])
        self.assertIn("> Pouvez-vous nous rappeler ?", formulaire.initial["texte"])

    def test_envoi_depuis_le_formulaire(self):
        self.client.force_login(self.equipe)
        with mock.patch("courriel.protocoles.smtplib.SMTP_SSL", FauxSMTP), \
                mock.patch("courriel.protocoles.imaplib.IMAP4_SSL", return_value=FauxIMAP({})):
            reponse = self.client.post(reverse("courriel:rediger"), {
                "compte": self.compte.pk, "a": "Élodie <elodie@client.fr>; autre@client.fr", "sujet": "Re: Demande de devis",
                "texte": "Bien reçu.", "mode": "repondre", "origine": self.recu.pk,
                "pieces": [SimpleUploadedFile("devis.pdf", b"%PDF", content_type="application/pdf")],
            })
        envoye = Courriel.objects.get(dossier=Courriel.Dossier.ENVOYES)
        self.assertRedirects(reponse, reverse("courriel:lire", args=[envoye.pk]), fetch_redirect_response=False)
        message, destinataires = FauxSMTP.envois[0]
        self.assertEqual(destinataires, ["elodie@client.fr", "autre@client.fr"])
        self.assertEqual(message["In-Reply-To"], "<a1@client.fr>")
        self.assertEqual(envoye.envoye_par, self.equipe)

    def test_adresse_invalide(self):
        self.client.force_login(self.equipe)
        reponse = self.client.post(reverse("courriel:rediger"), {"compte": self.compte.pk, "a": "pas-une-adresse", "texte": "x"})
        self.assertContains(reponse, "Adresse invalide")

    def test_ajout_de_boite_chiffre_teste_et_importe(self):
        self.client.force_login(self.equipe)
        with mock.patch("courriel.views.protocoles.tester") as tester, \
                mock.patch("courriel.views.protocoles.importer_historique", return_value=(12, 4)) as importer:
            self.client.post(reverse("courriel:compte_ajouter"), {
                "adresse": "devis@satkaar.io", "nom_expediteur": "Satkaar", "identifiant": "devis@satkaar.io",
                "mot_de_passe": "tres-secret", "imap_hote": "ssl0.ovh.net", "imap_port": 993,
                "smtp_hote": "ssl0.ovh.net", "smtp_port": 465, "smtp_securite": "ssl", "actif": "on",
            })
        boite_mail = CompteCourriel.objects.get(adresse="devis@satkaar.io")
        tester.assert_called_once()
        importer.assert_called_once_with(boite_mail, reception=200, envoyes=100)
        self.assertEqual(boite_mail.mot_de_passe, "tres-secret")
        self.assertNotIn(b"tres-secret", bytes(boite_mail.mot_de_passe_chiffre))

    def test_piece_jointe_toujours_telechargee(self):
        self.client.force_login(self.equipe)
        piece = self.recu.pieces_jointes.get()
        reponse = self.client.get(reverse("courriel:piece_jointe", args=[piece.pk]))
        self.assertIn("attachment", reponse["Content-Disposition"])
        self.assertEqual(b"".join(reponse.streaming_content), b"%PDF-1.4 cahier")

    def test_retrait_de_boite_efface_les_fichiers(self):
        self.client.force_login(self.equipe)
        chemin = Path(self.recu.pieces_jointes.get().fichier.path)
        self.assertTrue(chemin.exists())
        self.client.post(reverse("courriel:compte_supprimer", args=[self.compte.pk]))
        self.assertFalse(chemin.exists())
        self.assertFalse(Courriel.objects.exists())

    def test_lien_dans_la_barre_laterale(self):
        self.client.force_login(self.equipe)
        reponse = self.client.get(reverse("espace:tableau"))
        self.assertContains(reponse, reverse("courriel:boite"))
        self.assertContains(reponse, '<span class="app__compteur">1<span class="visuellement-cache"> non lu</span></span>', html=False)
        self.client.force_login(self.client_site)
        self.assertNotContains(self.client.get(reverse("espace:tableau")), reverse("courriel:boite"))

    def test_ancienne_adresse_redirigee(self):
        self.client.force_login(self.equipe)
        reponse = self.client.get(f"/espace/courriels/{self.recu.pk}/?images=1")
        self.assertRedirects(reponse, f"/espace/mail/{self.recu.pk}/?images=1", status_code=301)

    def test_mot_de_passe_saisi_plus_tard_declenche_l_import(self):
        """Fiche préparée sans mot de passe : le premier enregistrement complet importe l'historique."""
        self.client.force_login(self.equipe)
        preparee = CompteCourriel.objects.create(adresse="devis@satkaar.io", identifiant="devis@satkaar.io",
                                                 imap_hote="ssl0.ovh.net", smtp_hote="ssl0.ovh.net")
        with mock.patch("courriel.views.protocoles.tester"), \
                mock.patch("courriel.views.protocoles.importer_historique", return_value=(7, 2)) as importer:
            self.client.post(reverse("courriel:compte", args=[preparee.pk]), {
                "adresse": "devis@satkaar.io", "nom_expediteur": "Satkaar", "identifiant": "devis@satkaar.io",
                "mot_de_passe": "enfin-le-mot-de-passe", "imap_hote": "ssl0.ovh.net", "imap_port": 993,
                "smtp_hote": "ssl0.ovh.net", "smtp_port": 465, "smtp_securite": "ssl", "actif": "on",
            })
        importer.assert_called_once_with(preparee, reception=200, envoyes=100)
        preparee.refresh_from_db()
        self.assertEqual(preparee.mot_de_passe, "enfin-le-mot-de-passe")


class ClassementTests(Base):
    """Onglets de la boîte : catégories de Gmail quand elles existent, indices du message sinon."""

    def classer(self, **donnees):
        from .classement import classer

        return classer({"expediteur_adresse": "", "sujet": "", "entetes": {}, **donnees})

    def test_reseaux_sociaux_par_le_domaine(self):
        self.assertEqual(self.classer(expediteur_adresse="news@linkedin.com", sujet="Vous avez 3 invitations"),
                         Courriel.Categorie.RESEAUX)

    def test_notification_par_expediteur_automatique_ou_sujet(self):
        self.assertEqual(self.classer(expediteur_adresse="noreply@qonto.com", sujet="Votre relevé"),
                         Courriel.Categorie.NOTIFICATIONS)
        self.assertEqual(self.classer(expediteur_adresse="compta@client.fr", sujet="Facture 2026-014"),
                         Courriel.Categorie.NOTIFICATIONS)

    def test_promotion_par_desinscription(self):
        lettre = self.classer(expediteur_adresse="hello@boutique.fr", sujet="Nos nouveautés de septembre",
                              entetes={"list_unsubscribe": "<https://boutique.fr/stop>"})
        self.assertEqual(lettre, Courriel.Categorie.PROMOTIONS)

    def test_message_humain_reste_en_principale(self):
        self.assertEqual(self.classer(expediteur_adresse="elodie@client.fr", sujet="Re: Demande de devis"),
                         Courriel.Categorie.PRINCIPALE)

    def test_lien_de_desinscription_en_pied_de_message(self):
        """En-têtes perdus (message déjà importé) : le pied de page trahit l'envoi de masse."""
        from .classement import classer_enregistre

        message = Courriel(expediteur_adresse="contact@lettre.fr", sujet="Nouvelle mission freelance",
                           texte="Bonjour Damien," + " blabla" * 3000 + " Pour ne plus recevoir nos offres, cliquez ici.")
        self.assertEqual(classer_enregistre(message), Courriel.Categorie.PROMOTIONS)

    def test_les_onglets_de_gmail_priment(self):
        gmail = CompteCourriel(adresse="damien@gmail.com", identifiant="damien@gmail.com",
                               imap_hote="imap.gmail.com", smtp_hote="smtp.gmail.com")
        gmail.mot_de_passe = "secret"
        gmail.save()
        faux = FauxIMAP({b"7": message_brut(), b"8": message_brut("Offre", "<a2@pub.fr>", avec_piece=False)},
                        categories={"promotions": [b"8"]})
        with mock.patch("courriel.protocoles.imaplib.IMAP4_SSL", return_value=faux):
            protocoles.relever(gmail)
            self.assertEqual(protocoles.reclasser(gmail), 0)  # rien à changer au second passage
        self.assertEqual(Courriel.objects.get(compte=gmail, uid="8").categorie, Courriel.Categorie.PROMOTIONS)
        self.assertEqual(Courriel.objects.get(compte=gmail, uid="7").categorie, Courriel.Categorie.PRINCIPALE)


class OngletsTests(VuesTests):
    def test_barre_d_onglets_et_filtre(self):
        self.client.force_login(self.equipe)
        Courriel.objects.filter(pk=self.recu.pk).update(categorie=Courriel.Categorie.PRINCIPALE)
        protocoles.enregistrer(self.compte, protocoles.lire_message(message_brut("Soldes", "<p1@pub.fr>", avec_piece=False)),
                               uid="9", categorie=Courriel.Categorie.PROMOTIONS)
        page = self.client.get(reverse("courriel:boite"))
        onglets = {o["cle"]: o for o in page.context["onglets"]}
        self.assertEqual(onglets["principale"]["total"], 1)
        self.assertEqual(onglets["promotions"]["nouveaux"], 1)
        self.assertContains(page, "Promotions")
        promotions = self.client.get(reverse("courriel:boite"), {"categorie": "promotions"})
        self.assertEqual([c.sujet for c in promotions.context["page"].object_list], ["Soldes"])
        # Le message de l'onglet Principale n'est plus dans la liste (il reste en aperçu d'onglet).
        self.assertNotContains(promotions, reverse("courriel:lire", args=[self.recu.pk]))


class DetectionServeurTests(Base):
    """OVH répartit les boîtes sur plusieurs plateformes : on trouve la bonne toute seule."""

    def setUp(self):
        super().setUp()
        self.compte.imap_hote = "ssl0.ovh.net"
        self.compte.save()

    def _imap_qui_marche_sur(self, hote_valide):
        def fabrique(hote, *a, **k):
            if hote != hote_valide:
                raise imaplib.IMAP4.error("AUTHENTICATIONFAILED")
            return FauxIMAP({})
        return fabrique

    def test_serveur_email_pro_detecte(self):
        with mock.patch("courriel.protocoles.imaplib.IMAP4_SSL", side_effect=self._imap_qui_marche_sur("pro3.mail.ovh.net")):
            self.assertEqual(protocoles.detecter_serveur(self.compte), "pro3.mail.ovh.net")
        self.compte.refresh_from_db()
        self.assertEqual((self.compte.imap_hote, self.compte.smtp_hote, self.compte.smtp_port, self.compte.smtp_securite),
                         ("pro3.mail.ovh.net", "pro3.mail.ovh.net", 587, "starttls"))

    def test_aucun_serveur_ne_repond(self):
        with mock.patch("courriel.protocoles.imaplib.IMAP4_SSL", side_effect=self._imap_qui_marche_sur("nulle.part")):
            self.assertIsNone(protocoles.detecter_serveur(self.compte))

    def test_hors_ovh_on_ne_cherche_pas(self):
        gmail = CompteCourriel(adresse="x@gmail.com", identifiant="x@gmail.com", imap_hote="imap.gmail.com")
        gmail.mot_de_passe = "secret"
        gmail.save()
        with mock.patch("courriel.protocoles.imaplib.IMAP4_SSL") as ouvrir:
            self.assertIsNone(protocoles.detecter_serveur(gmail))
        ouvrir.assert_not_called()

    def test_formulaire_corrige_le_serveur(self):
        utilisateur = get_user_model().objects.create_user("chef", "chef@satkaar.io", "x", is_staff=True)
        self.client.force_login(utilisateur)
        with mock.patch("courriel.views.protocoles.tester", side_effect=protocoles.ErreurCourriel("refusé")), \
                mock.patch("courriel.views.protocoles.detecter_serveur", return_value="pro3.mail.ovh.net") as detecter, \
                mock.patch("courriel.views.protocoles.importer_historique", return_value=(3, 1)):
            reponse = self.client.post(reverse("courriel:compte", args=[self.compte.pk]), {
                "adresse": self.compte.adresse, "nom_expediteur": "Satkaar", "identifiant": self.compte.identifiant,
                "mot_de_passe": "secret", "imap_hote": "ssl0.ovh.net", "imap_port": 993,
                "smtp_hote": "ssl0.ovh.net", "smtp_port": 465, "smtp_securite": "ssl", "actif": "on",
            }, follow=True)
        detecter.assert_called_once()
        self.assertContains(reponse, "Serveur corrigé automatiquement : pro3.mail.ovh.net")

