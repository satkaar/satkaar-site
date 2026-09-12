import datetime
import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import detection
from .analyse import analyser
from .graphiques import graduations
from .models import Evenement, Mesure, PageVue, PassageRobot

NAVIGATEUR = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"


class CollecteTests(TestCase):
    def setUp(self):
        cache.clear()

    def visiter(self, chemin="/", **entetes):
        entetes.setdefault("HTTP_USER_AGENT", NAVIGATEUR)
        return self.client.get(chemin, **entetes)

    def test_page_vue_enregistree_sans_ip(self):
        self.visiter("/conseil/", HTTP_REFERER="https://www.google.fr/", HTTP_ACCEPT_LANGUAGE="fr-FR")
        vue = PageVue.objects.get()
        self.assertEqual((vue.chemin, vue.source, vue.referent), ("/conseil/", "moteur", "google.fr"))
        self.assertEqual((vue.appareil, vue.navigateur, vue.systeme, vue.langue), ("Ordinateur", "Chrome", "macOS", "fr"))
        self.assertEqual(len(vue.visiteur), 16)
        self.assertNotIn("127.0.0.1", str(vue.__dict__))

    def test_assistant_ia_et_campagne(self):
        self.visiter("/", HTTP_REFERER="https://chatgpt.com/")
        self.visiter("/?utm_source=linkedin&utm_campaign=lancement")
        sources = sorted(PageVue.objects.values_list("source", flat=True))
        self.assertEqual(sources, ["campagne", "ia"])

    def test_refus_du_suivi_respecte(self):
        self.visiter("/", HTTP_DNT="1")
        self.visiter("/", HTTP_SEC_GPC="1")
        self.assertFalse(PageVue.objects.exists())

    def test_robots_comptes_a_part(self):
        self.visiter("/llms.txt", HTTP_USER_AGENT="Mozilla/5.0 (compatible; GPTBot/1.2)")
        self.visiter("/", HTTP_USER_AGENT="Mozilla/5.0 (compatible; Googlebot/2.1)")
        self.assertFalse(PageVue.objects.exists())
        self.assertEqual(sorted(PassageRobot.objects.values_list("famille", flat=True)), ["ia", "moteur"])

    def test_espace_et_equipe_non_mesures(self):
        self.visiter("/espace/connexion/")
        equipe = get_user_model().objects.create_user("equipe", "equipe@satkaar.io", "x", is_staff=True)
        self.client.force_login(equipe)
        self.visiter("/")
        self.assertFalse(PageVue.objects.exists())

    def test_collecte_mesure_et_evenement(self):
        entetes = {"HTTP_USER_AGENT": NAVIGATEUR, "HTTP_ORIGIN": "http://testserver"}
        corps = {"type": "page", "chemin": "/conseil/", "temps_actif": 42, "defilement": 80, "lcp": 1200, "cls": 0.02}
        self.assertEqual(self.client.post("/mesure/", json.dumps(corps), content_type="text/plain", **entetes).status_code, 204)
        self.client.post("/mesure/", json.dumps({"type": "telephone", "chemin": "/contact/", "cible": "+33634618697"}),
                         content_type="text/plain", **entetes)
        mesure = Mesure.objects.get()
        self.assertEqual((mesure.temps_actif_s, mesure.defilement, mesure.lcp_ms), (42, 80, 1200))
        self.assertEqual(Evenement.objects.get().type, "telephone")

    def test_collecte_refuse_une_autre_origine(self):
        reponse = self.client.post("/mesure/", "{}", content_type="text/plain",
                                   HTTP_USER_AGENT=NAVIGATEUR, HTTP_ORIGIN="http://testserver.pirate.com")
        self.assertEqual(reponse.status_code, 400)

    def test_evenement_serveur_non_falsifiable(self):
        self.client.post("/mesure/", json.dumps({"type": "connexion", "chemin": "/"}), content_type="text/plain",
                         HTTP_USER_AGENT=NAVIGATEUR, HTTP_ORIGIN="http://testserver")
        self.assertFalse(Evenement.objects.exists())


class AnalyseTests(TestCase):
    def test_visites_rebond_et_sources(self):
        maintenant = timezone.now()
        avant = maintenant - datetime.timedelta(hours=3)
        for minutes, chemin in [(0, "/"), (5, "/conseil/"), (70, "/formation/")]:
            PageVue.objects.create(horodatage=avant + datetime.timedelta(minutes=minutes), chemin=chemin,
                                   visiteur="a" * 16, source="direct" if minutes == 0 else "interne")
        PageVue.objects.create(horodatage=avant, chemin="/", visiteur="b" * 16, source="ia", referent="chatgpt.com")
        r = analyser(7, maintenant)
        kpi = {t["cle"]: t["valeur"] for t in r["kpi"]}
        self.assertEqual((kpi["visiteurs"], kpi["visites"], kpi["pages_vues"]), (2, 3, 4))
        self.assertEqual(kpi["taux_rebond"], 66.7)  # deux visites d'une seule page sur trois
        self.assertEqual(r["assistants_ia"][0]["libelle"], "chatgpt.com")

    def test_graduations_rondes(self):
        self.assertEqual(graduations(37), [0, 10, 20, 30, 40])
        self.assertEqual(graduations(0), [0, 1])


class StatistiquesTests(TestCase):
    def test_reservees_a_l_equipe(self):
        client_satkaar = get_user_model().objects.create_user("client", "client@example.fr", "x")
        self.client.force_login(client_satkaar)
        self.assertEqual(self.client.get(reverse("espace:statistiques")).status_code, 404)
        self.assertNotContains(self.client.get(reverse("espace:tableau")), "Statistiques")

    def test_tableau_de_bord_de_l_equipe(self):
        equipe = get_user_model().objects.create_user("equipe", "equipe@satkaar.io", "x", is_staff=True)
        self.client.force_login(equipe)
        reponse = self.client.get(reverse("espace:statistiques") + "?periode=7")
        self.assertEqual(reponse.status_code, 200)
        for texte in ["Chiffres clés", "Assistants IA", "Robots des moteurs et des IA", "Performance ressentie",
                      "Santé technique du site", "Taux de rebond", "Taux de conversion"]:
            self.assertContains(reponse, texte)


class DetectionTests(TestCase):
    def test_referents(self):
        self.assertEqual(detection.source("https://gemini.google.com/app", "satkaar.io", ""), ("ia", "gemini.google.com"))
        self.assertEqual(detection.source("https://www.satkaar.io/conseil/", "satkaar.io", ""), ("interne", ""))
