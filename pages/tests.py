import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import jours_ouvres_a_venir
from .models import DemandeDemonstration


class RappelDansLaDemandeTests(TestCase):
    url = reverse("pages:contact")

    def envoyer(self, **champs):
        donnees = {
            "nom": "Claire Martin",
            "organisation": "Manosque",
            "courriel": "claire@example.fr",
            "sujet": "vanessa",
            "telephone": "06 12 34 56 78",
            "rappel_jour": "",
            "rappel_heure": "",
        }
        donnees.update(champs)
        return self.client.post(self.url, donnees)

    def test_jours_proposes_ouvres_sur_deux_mois(self):
        jours = jours_ouvres_a_venir(datetime.date(2026, 9, 11))  # un vendredi
        self.assertEqual(jours[0], datetime.date(2026, 9, 14))
        self.assertEqual(jours[-1], datetime.date(2026, 11, 11))  # un mercredi
        self.assertTrue(all(jour.weekday() < 5 for jour in jours))

    def test_fin_de_mois_ramenee_au_dernier_jour(self):
        jours = jours_ouvres_a_venir(datetime.date(2026, 12, 31))
        self.assertEqual(jours[-1], datetime.date(2027, 2, 26))  # 28 février = dimanche

    def test_peu_importe_par_defaut(self):
        reponse = self.envoyer()
        self.assertRedirects(reponse, f"{self.url}?envoye=1", fetch_redirect_response=False)
        demande = DemandeDemonstration.objects.get()
        self.assertIsNone(demande.rappel_jour)
        self.assertIsNone(demande.rappel_heure)

    def test_creneau_enregistre_et_rappele_dans_la_confirmation(self):
        jour = jours_ouvres_a_venir(timezone.localdate())[0]
        self.envoyer(rappel_jour=jour.isoformat(), rappel_heure="10:30")
        demande = DemandeDemonstration.objects.get()
        self.assertEqual(demande.rappel_jour, jour)
        self.assertEqual(demande.rappel_heure, datetime.time(10, 30))

        page = self.client.get(f"{self.url}?envoye=1")
        self.assertContains(page, "Nous vous rappelons le")
        self.assertContains(page, "vers 10 h 30")

    def test_rappel_sans_telephone_refuse(self):
        reponse = self.envoyer(telephone="", rappel_heure="09:00")
        self.assertContains(reponse, "Indiquez un numéro pour que nous puissions vous rappeler.")
        self.assertFalse(DemandeDemonstration.objects.exists())

    def test_jour_hors_liste_refuse(self):
        samedi = datetime.date(2026, 9, 12)
        reponse = self.envoyer(rappel_jour=samedi.isoformat())
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(DemandeDemonstration.objects.exists())

    def test_choix_conserve_apres_erreur(self):
        jour = jours_ouvres_a_venir(timezone.localdate())[2]
        reponse = self.envoyer(nom="", rappel_jour=jour.isoformat(), rappel_heure="15:00")
        html = reponse.content.decode()
        self.assertIn(f'value="{jour.isoformat()}" checked', html)
        self.assertIn('value="15:00" checked', html)


class PagesDuGroupeTests(TestCase):
    def test_pages_publiques(self):
        for nom in ["accueil", "conseil", "formation", "logiciels", "isidor", "katarina", "vanessa", "bernard",
                    "references", "a_propos", "souverainete", "contact"]:
            with self.subTest(page=nom):
                self.assertEqual(self.client.get(reverse(f"pages:{nom}")).status_code, 200)

    def test_accueil_presente_les_deux_metiers_et_les_trois_logiciels(self):
        page = self.client.get(reverse("pages:accueil"))
        for texte in ["Conseil en IA, data et systèmes d'information", "Isidor", "Katarina", "Vanessa", "Bernard"]:
            self.assertContains(page, texte)
        self.assertNotContains(page, "Marine")

    def test_sujet_preselectionne_depuis_une_page_produit(self):
        page = self.client.get(reverse("pages:contact") + "?sujet=bernard")
        self.assertContains(page, '<option value="bernard" selected>')

    def test_sujet_inconnu_ignore(self):
        page = self.client.get(reverse("pages:contact") + "?sujet=pirate")
        self.assertContains(page, '<option value="" selected>')
