import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import ESSAIS_MAX
from .models import Document, Projet

DOSSIER_TEST = tempfile.mkdtemp()


@override_settings(ESPACE_DOCUMENTS_ROOT=DOSSIER_TEST)
class EspaceClientTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(DOSSIER_TEST, ignore_errors=True)

    def setUp(self):
        cache.clear()
        Utilisateur = get_user_model()
        self.claire = Utilisateur.objects.create_user("claire", "claire@example.fr", "mot-de-passe-solide-1")
        self.autre = Utilisateur.objects.create_user("autre", "autre@example.fr", "mot-de-passe-solide-2")
        self.projet = Projet.objects.create(
            client=self.claire, titre="Diagnostic data", type=Projet.Type.CONSEIL, avancement=40
        )
        self.document = Document.objects.create(
            client=self.claire, projet=self.projet, titre="Facture 1", categorie=Document.Categorie.FACTURE,
            fichier=SimpleUploadedFile("facture-1.pdf", b"%PDF-1.4 test"),
        )
        self.document_autre = Document.objects.create(
            client=self.autre, titre="Document d'un autre", fichier=SimpleUploadedFile("secret.pdf", b"secret"),
        )

    def connexion(self, courriel, mot_de_passe):
        return self.client.post(reverse("espace:connexion"), {"username": courriel, "password": mot_de_passe})

    def test_tableau_reserve_aux_clients_connectes(self):
        reponse = self.client.get(reverse("espace:tableau"))
        self.assertRedirects(reponse, f"{reverse('espace:connexion')}?next={reverse('espace:tableau')}")

    def test_connexion_par_courriel_sans_tenir_compte_de_la_casse(self):
        reponse = self.connexion("Claire@Example.fr", "mot-de-passe-solide-1")
        self.assertRedirects(reponse, reverse("espace:tableau"))
        page = self.client.get(reverse("espace:tableau"))
        self.assertContains(page, "Diagnostic data")
        self.assertContains(page, "Facture 1")
        self.assertNotContains(page, "Document d'un autre")

    def test_mauvais_mot_de_passe(self):
        reponse = self.connexion("claire@example.fr", "faux")
        self.assertContains(reponse, "Courriel ou mot de passe incorrect.")

    def test_trop_de_tentatives_bloque_meme_le_bon_mot_de_passe(self):
        for _ in range(ESSAIS_MAX):
            self.connexion("claire@example.fr", "faux")
        reponse = self.connexion("claire@example.fr", "mot-de-passe-solide-1")
        self.assertContains(reponse, "Trop de tentatives de connexion")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_telechargement_de_son_document(self):
        self.client.force_login(self.claire)
        reponse = self.client.get(reverse("espace:telecharger", args=[self.document.pk]))
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("attachment", reponse["Content-Disposition"])
        self.assertEqual(b"".join(reponse.streaming_content), b"%PDF-1.4 test")

    def test_document_d_un_autre_client_introuvable(self):
        self.client.force_login(self.claire)
        reponse = self.client.get(reverse("espace:telecharger", args=[self.document_autre.pk]))
        self.assertEqual(reponse.status_code, 404)

    def test_telechargement_refuse_sans_connexion(self):
        reponse = self.client.get(reverse("espace:telecharger", args=[self.document.pk]))
        self.assertEqual(reponse.status_code, 302)

    def test_filtre_des_documents(self):
        self.client.force_login(self.claire)
        page = self.client.get(reverse("espace:documents") + "?categorie=livrable")
        self.assertContains(page, "Aucun document dans cette catégorie.")

    def test_deconnexion(self):
        self.client.force_login(self.claire)
        reponse = self.client.post(reverse("espace:deconnexion"))
        self.assertRedirects(reponse, reverse("pages:accueil"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_mot_de_passe_oublie_envoie_un_lien(self):
        reponse = self.client.post(reverse("espace:reinitialisation"), {"email": "claire@example.fr"})
        self.assertRedirects(reponse, reverse("espace:reinitialisation_envoyee"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/espace/reinitialiser/", mail.outbox[0].body)

    def test_lien_connexion_dans_l_en_tete(self):
        self.assertContains(self.client.get(reverse("pages:accueil")), "Connexion")
        self.client.force_login(self.claire)
        self.assertContains(self.client.get(reverse("pages:accueil")), "Mon espace")
