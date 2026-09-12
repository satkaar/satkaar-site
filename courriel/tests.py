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
    def __init__(self, messages):
        self.messages = messages
        self.commandes = []
        self.lecture_seule = None
        self.depose = None

    def login(self, identifiant, mot_de_passe):
        if mot_de_passe != "secret":
            raise imaplib.IMAP4.error("AUTHENTICATIONFAILED")

    def select(self, dossier, readonly=False):
        self.lecture_seule = readonly
        return "OK", [str(len(self.messages)).encode()]

    def uid(self, commande, *arguments):
        self.commandes.append((commande, *arguments))
        if commande == "search":
            return "OK", [b" ".join(self.messages)]
        uid, parties = arguments
        return "OK", [(b"1 (UID " + uid + b" BODY[] {100}", self.messages[uid]), b")"]

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
        self.assertTrue(all(c[2] == "(BODY.PEEK[])" for c in faux.commandes if c[0] == "fetch"))
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

    def test_ajout_de_boite_chiffre_et_teste(self):
        self.client.force_login(self.equipe)
        with mock.patch("courriel.views.protocoles.tester") as tester:
            self.client.post(reverse("courriel:compte_ajouter"), {
                "adresse": "devis@satkaar.io", "nom_expediteur": "Satkaar", "identifiant": "devis@satkaar.io",
                "mot_de_passe": "tres-secret", "imap_hote": "ssl0.ovh.net", "imap_port": 993,
                "smtp_hote": "ssl0.ovh.net", "smtp_port": 465, "smtp_securite": "ssl", "actif": "on",
            })
        boite_mail = CompteCourriel.objects.get(adresse="devis@satkaar.io")
        tester.assert_called_once()
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
