from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from pages.models import DemandeDemonstration

from . import calendrier
from .models import Evenement


def moment(jour, heure, minute=0):
    return timezone.make_aware(datetime.combine(jour, time(heure, minute)))


class AgendaTests(TestCase):
    def setUp(self):
        utilisateurs = get_user_model().objects
        self.equipe = utilisateurs.create_user("equipe", "damien@satkaar.io", "x", is_staff=True, first_name="Damien", last_name="Marque")
        self.client_site = utilisateurs.create_user("client", "client@mairie.fr", "x")
        self.lundi = calendrier.lundi_de(timezone.localdate())
        self.rdv = Evenement.objects.create(titre="Comité de pilotage Vanessa", organisation="CCFML", lieu="Forcalquier",
                                            debut=moment(self.lundi, 10), fin=moment(self.lundi, 11, 30))

    def test_reserve_a_l_equipe(self):
        self.assertEqual(self.client.get(reverse("agenda:semaine")).status_code, 302)
        self.client.force_login(self.client_site)
        for url in (reverse("agenda:semaine"), reverse("agenda:mois"), reverse("agenda:jour"),
                    reverse("agenda:evenement", args=[self.rdv.pk])):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_semaine_affiche_evenements_et_rappels(self):
        DemandeDemonstration.objects.create(nom="Claire Robin", organisation="Mairie de Sisteron", courriel="c@sisteron.fr",
                                            telephone="0600000000", rappel_jour=self.lundi + timedelta(days=1), rappel_heure=time(14))
        self.client.force_login(self.equipe)
        page = self.client.get(reverse("agenda:semaine"))
        self.assertContains(page, "Comité de pilotage Vanessa")
        self.assertContains(page, "Rappeler Claire Robin")
        self.assertContains(page, "De 10:00 à 11:30")

    def test_chevauchements_cote_a_cote(self):
        a = calendrier.Element("A", "interne", moment(self.lundi, 9), moment(self.lundi, 11), "/a")
        b = calendrier.Element("B", "interne", moment(self.lundi, 10), moment(self.lundi, 12), "/b")
        c = calendrier.Element("C", "interne", moment(self.lundi, 13), moment(self.lundi, 14), "/c")
        places = calendrier._placer([(e, e.debut, e.fin) for e in (a, b, c)], moment(self.lundi, 0))
        self.assertEqual([(p["voie"], p["voies"]) for p in places], [(0, 2), (1, 2), (0, 1)])
        self.assertEqual(places[0]["haut_pct"], 37.5)  # 9 h sur une grille de 24 h

    def test_creation_avec_visio_et_participants(self):
        self.client.force_login(self.equipe)
        reponse = self.client.post(reverse("agenda:ajouter"), {
            "titre": "Formation IA générative", "categorie": "formation", "date_debut": "2026-10-06",
            "heure_debut": "09:00", "heure_fin": "17:00", "generer_visio": "on", "participants": [self.equipe.pk],
        })
        evenement = Evenement.objects.get(titre="Formation IA générative")
        self.assertRedirects(reponse, reverse("agenda:evenement", args=[evenement.pk]))
        self.assertTrue(evenement.lien_visio.startswith("https://meet.jit.si/Satkaar-formation-ia-generative-"))
        self.assertEqual(timezone.localtime(evenement.debut).hour, 9)
        self.assertEqual(evenement.cree_par, self.equipe)
        self.assertEqual(list(evenement.participants.all()), [self.equipe])

    def test_journee_entiere_sur_plusieurs_jours(self):
        self.client.force_login(self.equipe)
        self.client.post(reverse("agenda:ajouter"), {"titre": "Salon des maires", "categorie": "autre", "journee_entiere": "on",
                                                     "date_debut": "2026-11-24", "date_fin": "2026-11-26"})
        evenement = Evenement.objects.get(titre="Salon des maires")
        self.assertEqual(timezone.localtime(evenement.fin).date(), date(2026, 11, 27))
        page = self.client.get(reverse("agenda:evenement", args=[evenement.pk]))
        self.assertContains(page, "Du mardi 24 novembre au jeudi 26 novembre 2026")

    def test_fin_avant_debut_refusee(self):
        self.client.force_login(self.equipe)
        reponse = self.client.post(reverse("agenda:ajouter"), {"titre": "X", "categorie": "interne", "date_debut": "2026-10-06",
                                                               "heure_debut": "15:00", "heure_fin": "14:00"})
        self.assertContains(reponse, "L&#x27;heure de fin doit suivre l&#x27;heure de début.")

    def test_modification_et_suppression(self):
        self.client.force_login(self.equipe)
        page = self.client.get(reverse("agenda:modifier", args=[self.rdv.pk]))
        self.assertEqual(page.context["form"].initial["heure_fin"], time(11, 30))
        self.client.post(reverse("agenda:supprimer", args=[self.rdv.pk]))
        self.assertFalse(Evenement.objects.exists())

    def test_mois_et_export_ics(self):
        self.client.force_login(self.equipe)
        self.assertContains(self.client.get(reverse("agenda:mois")), "Comité de pilotage Vanessa")
        reponse = self.client.get(reverse("agenda:ics", args=[self.rdv.pk]))
        self.assertEqual(reponse["Content-Type"], "text/calendar; charset=utf-8")
        contenu = reponse.content.decode()
        self.assertIn("SUMMARY:Comité de pilotage Vanessa", contenu)
        self.assertIn(f"UID:agenda-{self.rdv.pk}@satkaar.io", contenu)
        self.assertTrue(all(len(l.encode()) <= 75 for l in contenu.split("\r\n")))

    def test_invitation_par_mail_preremplie(self):
        self.client.force_login(self.equipe)
        page = self.client.get(reverse("agenda:evenement", args=[self.rdv.pk]))
        self.assertContains(page, reverse("courriel:rediger") + "?sujet=Invitation")

    def test_liens_dans_la_barre_laterale(self):
        self.client.force_login(self.equipe)
        page = self.client.get(reverse("espace:tableau"))
        self.assertContains(page, reverse("agenda:mois"))
        self.assertContains(page, "<span>Mail</span>")
        for libelle in ("Tableau de bord", "Statistiques", "<span>Agenda</span>"):
            self.assertContains(page, libelle)
        self.assertNotContains(page, "Communication")

    def test_vue_jour_et_selecteur(self):
        self.client.force_login(self.equipe)
        page = self.client.get(reverse("agenda:jour_du", args=[self.lundi.year, self.lundi.month, self.lundi.day]))
        self.assertContains(page, "Comité de pilotage Vanessa")
        self.assertContains(page, "--nb-jours: 1")
        self.assertContains(page, 'aria-current="true">Jour</a>')
        self.assertContains(self.client.get(reverse("agenda:mois")), 'aria-current="true">Mois</a>')
