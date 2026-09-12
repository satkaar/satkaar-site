from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from pages.models import DemandeDemonstration

from .models import Contact, Note


class ContactsTests(TestCase):
    def setUp(self):
        utilisateurs = get_user_model().objects
        self.equipe = utilisateurs.create_user("equipe", "damien@satkaar.io", "x", is_staff=True, first_name="Damien")
        self.client_site = utilisateurs.create_user("client", "client@mairie.fr", "x")
        self.isidor = Contact.objects.create(nom="Yannick Pastre", organisation="GAEC Pastre", produit="isidor", statut="demo",
                                             taille=120, prochaine_relance=timezone.localdate() - timedelta(days=1))
        self.vanessa = Contact.objects.create(nom="Claire Robin", organisation="Mairie de Sisteron", produit="vanessa",
                                              statut="client", montant=Decimal("4800"))

    def test_reserve_a_l_equipe(self):
        self.assertEqual(self.client.get(reverse("contacts:liste")).status_code, 302)
        self.client.force_login(self.client_site)
        for url in (reverse("contacts:liste"), reverse("contacts:fiche", args=[self.isidor.pk]), reverse("contacts:export")):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_estimation_isidor_d_apres_la_surface(self):
        # (29,90 € + 0,33 € × 120 ha) × 12 mois = 834 €
        self.assertEqual(self.isidor.potentiel, Decimal("834"))
        self.assertTrue(self.isidor.estime)
        self.assertEqual(self.vanessa.potentiel, Decimal("4800"))

    def test_demande_du_site_devient_un_lead(self):
        demande = DemandeDemonstration.objects.create(nom="Paul Nicolas", organisation="EARL Nicolas", courriel="paul@earl.fr",
                                                      sujet="isidor", message="80 ha de vignes", rappel_jour=timezone.localdate())
        lead = Contact.objects.get(courriel="paul@earl.fr")
        self.assertEqual((lead.produit, lead.statut, lead.source, lead.demande), ("isidor", "lead", "site", demande))
        self.assertEqual(lead.prochaine_relance, timezone.localdate())
        self.assertIn("80 ha de vignes", lead.notes.get().texte)
        # Une deuxième demande de la même personne pour le même produit s'ajoute à la fiche.
        DemandeDemonstration.objects.create(nom="Paul Nicolas", organisation="EARL Nicolas", courriel="PAUL@earl.fr", sujet="isidor")
        self.assertEqual(Contact.objects.filter(courriel__iexact="paul@earl.fr").count(), 1)
        self.assertEqual(lead.notes.count(), 2)

    def test_liste_synthese_par_logiciel(self):
        self.client.force_login(self.equipe)
        page = self.client.get(reverse("contacts:liste"))
        resumes = {r["cle"]: r for r in page.context["resumes"]}
        self.assertEqual(list(resumes), ["isidor", "vanessa", "bernard"])
        self.assertEqual((resumes["isidor"]["leads"], resumes["isidor"]["potentiel"]), (1, Decimal("834")))
        self.assertEqual((resumes["vanessa"]["clients"], resumes["vanessa"]["revenu"]), (1, Decimal("4800")))
        self.assertEqual(page.context["totaux"]["a_relancer"], 1)
        self.assertContains(page, "Yannick Pastre")

    def test_filtres_et_vue_liste(self):
        self.client.force_login(self.equipe)
        page = self.client.get(reverse("contacts:liste"), {"produit": "vanessa", "vue": "liste"})
        self.assertContains(page, "Claire Robin")
        self.assertNotContains(page, "GAEC Pastre")
        page = self.client.get(reverse("contacts:liste"), {"relance": "1"})
        self.assertEqual([c.nom for c in page.context["contacts"]], ["Yannick Pastre"])

    def test_changement_d_etape_trace_dans_l_historique(self):
        self.client.force_login(self.equipe)
        self.client.post(reverse("contacts:etape", args=[self.isidor.pk]), {"statut": "proposition"})
        self.isidor.refresh_from_db()
        self.assertEqual(self.isidor.statut, "proposition")
        self.assertEqual(self.isidor.notes.get().texte, "Étape : Démo → Proposition")

    def test_creation_fiche_et_note(self):
        self.client.force_login(self.equipe)
        reponse = self.client.post(reverse("contacts:ajouter"), {
            "nom": "Bernard Desmar", "organisation": "Net Patrimoine & Capitaux", "produit": "bernard", "statut": "client",
            "source": "recommandation", "taille": "350", "montant": "6000", "responsable": self.equipe.pk,
        })
        contact = Contact.objects.get(nom="Bernard Desmar")
        self.assertRedirects(reponse, reverse("contacts:fiche", args=[contact.pk]))
        self.client.post(reverse("contacts:note", args=[contact.pk]), {"type": "appel", "texte": "Point sur les quittances."})
        note = contact.notes.get()
        self.assertEqual((note.type, note.auteur), (Note.Type.APPEL, self.equipe))
        page = self.client.get(reverse("contacts:fiche", args=[contact.pk]))
        self.assertContains(page, "Point sur les quittances.")
        self.assertContains(page, "Biens gérés")

    def test_export_csv(self):
        self.client.force_login(self.equipe)
        reponse = self.client.get(reverse("contacts:export"), {"produit": "isidor"})
        contenu = reponse.content.decode("utf-8-sig")
        self.assertIn("Yannick Pastre;GAEC Pastre", contenu)
        self.assertIn("834", contenu)
        self.assertNotIn("Claire Robin", contenu)

    def test_rendez_vous_prerempli_dans_l_agenda(self):
        self.client.force_login(self.equipe)
        page = self.client.get(reverse("contacts:fiche", args=[self.isidor.pk]))
        lien = page.context["rendez_vous"]
        formulaire = self.client.get(lien).context["form"]
        self.assertEqual(formulaire.initial["titre"], "Rendez-vous Isidor — GAEC Pastre")
        self.assertEqual(formulaire.initial["organisation"], "GAEC Pastre")

    def test_lien_dans_la_barre(self):
        self.client.force_login(self.equipe)
        page = self.client.get(reverse("espace:tableau"))
        self.assertContains(page, reverse("contacts:liste"))
