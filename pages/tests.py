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


class ReferencementTests(TestCase):
    PAGES = ["accueil", "conseil", "formation", "logiciels", "isidor", "katarina", "vanessa",
             "bernard", "references", "a_propos", "contact"]

    def html(self, nom):
        return self.client.get(reverse(f"pages:{nom}")).content.decode()

    def test_titres_uniques_et_balises_essentielles(self):
        import re
        titres = set()
        for nom in self.PAGES:
            with self.subTest(page=nom):
                html = self.html(nom)
                titres.add(re.search(r"<title>(.*?)</title>", html, re.S).group(1))
                self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)
                self.assertIn('<link rel="canonical"', html)
                self.assertIn('<meta property="og:image"', html)
                self.assertIn('name="description"', html)
        self.assertEqual(len(titres), len(self.PAGES))

    def test_donnees_structurees_valides(self):
        import json
        import re
        attendus = {"accueil": "FAQPage", "conseil": "FAQPage", "isidor": "SoftwareApplication",
                    "vanessa": "SoftwareApplication", "a_propos": "BreadcrumbList"}
        for nom, type_attendu in attendus.items():
            with self.subTest(page=nom):
                blocs = re.findall(r'<script type="application/ld\+json">(.*?)</script>', self.html(nom), re.S)
                donnees = [json.loads(b) for b in blocs]
                types = {d.get("@type") for d in donnees} | {g["@type"] for d in donnees for g in d.get("@graph", [])}
                self.assertIn("Organization", types)
                self.assertIn(type_attendu, types)

    def test_faq_affichee_correspond_aux_donnees_structurees(self):
        from . import seo
        html = self.html("formation")
        for question, reponse in seo.FAQ["formation"]:
            self.assertIn(question.replace("'", "&#x27;"), html)

    def test_robots_sitemap_llms(self):
        robots = self.client.get("/robots.txt").content.decode()
        self.assertIn("Disallow: /espace/", robots)
        self.assertIn("User-agent: GPTBot", robots)
        self.assertIn("sitemap.xml", robots)
        sitemap = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("/logiciels/isidor/", sitemap)
        self.assertNotIn("/espace/", sitemap)
        llms = self.client.get("/llms.txt").content.decode()
        self.assertTrue(llms.startswith("# Satkaar"))
        self.assertIn("Qualiopi", llms)
        self.assertNotIn("&#x27;", llms)

    def test_espace_client_hors_index(self):
        html = self.client.get(reverse("espace:connexion")).content.decode()
        self.assertIn('content="noindex, nofollow"', html)


class CreneauxBranchesSurLAgendaTests(TestCase):
    """Un créneau pris dans l'agenda de l'équipe ou par une autre demande ne se réserve pas deux fois."""

    url = reverse("pages:contact")

    def setUp(self):
        from agenda.models import Evenement

        self.jour = jours_ouvres_a_venir(timezone.localdate())[0]
        self.lendemain = jours_ouvres_a_venir(timezone.localdate())[1]
        debut = timezone.make_aware(datetime.datetime.combine(self.jour, datetime.time(10, 0)))
        Evenement.objects.create(titre="Comité de pilotage", debut=debut, fin=debut + datetime.timedelta(hours=1))
        Evenement.objects.create(titre="Salon", journee_entiere=True,
                                 debut=timezone.make_aware(datetime.datetime.combine(self.lendemain, datetime.time(0))),
                                 fin=timezone.make_aware(datetime.datetime.combine(self.lendemain, datetime.time(0))) + datetime.timedelta(days=1))
        DemandeDemonstration.objects.create(nom="Autre visiteur", organisation="X", courriel="x@x.fr", telephone="0600000000",
                                            rappel_jour=self.jour, rappel_heure=datetime.time(15, 0))

    def envoyer(self, heure):
        return self.client.post(self.url, {"nom": "Claire Martin", "organisation": "Manosque", "courriel": "claire@example.fr",
                                           "sujet": "vanessa", "telephone": "06 12 34 56 78",
                                           "rappel_jour": self.jour.isoformat(), "rappel_heure": heure})

    def test_creneaux_pris(self):
        from agenda.disponibilites import creneaux_pris

        heures = ["09:30", "10:00", "10:30", "11:00", "15:00", "15:30"]
        pris = creneaux_pris([self.jour, self.lendemain], heures)
        self.assertEqual(pris[self.jour.isoformat()], ["10:00", "10:30", "15:00"])  # 10 h – 11 h, puis la demande de 15 h
        self.assertEqual(pris[self.lendemain.isoformat()], heures)  # journée entière : tout est pris

    def test_page_transmet_les_creneaux_pris(self):
        page = self.client.get(self.url)
        self.assertEqual(page.context["form"].creneaux_pris[self.jour.isoformat()], ["10:00", "10:30", "15:00"])
        self.assertContains(page, 'id="creneaux-pris"')
        self.assertContains(page, f'value="{self.lendemain.isoformat()}" disabled')

    def test_double_reservation_refusee(self):
        reponse = self.envoyer("10:30")
        self.assertContains(reponse, "Ce créneau vient d&#x27;être réservé")
        self.assertEqual(DemandeDemonstration.objects.count(), 1)

    def test_creneau_libre_accepte_puis_bloque(self):
        reponse = self.envoyer("11:00")
        self.assertRedirects(reponse, f"{self.url}?envoye=1", fetch_redirect_response=False)
        self.assertContains(self.envoyer("11:00"), "Ce créneau vient d&#x27;être réservé")


class PreproductionTests(TestCase):
    def test_indexation_autorisee_par_defaut(self):
        reponse = self.client.get(reverse("robots"))
        self.assertNotIn("Disallow: /\n", reponse.content.decode())
        self.assertNotIn("X-Robots-Tag", reponse.headers)

    def test_preproduction_interdite_aux_moteurs(self):
        from django.test import override_settings

        with override_settings(NOINDEX=True):
            self.assertEqual(self.client.get(reverse("robots")).content.decode(), "User-agent: *\nDisallow: /\n")
            self.assertEqual(self.client.get(reverse("pages:accueil"))["X-Robots-Tag"], "noindex, nofollow")
