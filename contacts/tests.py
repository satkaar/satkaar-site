import shutil
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
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
            "nom": "Bernard Desmar", "organisation": "Net Patrimoine & Capitaux", "sens": "entrant",
            "produit": "bernard", "statut": "client", "source": "recommandation", "taille": "350",
            "montant": "6000", "responsable": self.equipe.pk,
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


class SortantsTests(TestCase):
    """Deux pipelines séparés : ce qui arrive (entrants) et ce qu'on va chercher (sortants)."""

    def setUp(self):
        self.equipe = get_user_model().objects.create_user("equipe2", "equipe@satkaar.io", "x", is_staff=True)
        self.client.force_login(self.equipe)
        self.entrant = Contact.objects.create(nom="Claire Robin", organisation="Mairie de Sisteron",
                                              produit="vanessa", statut="lead", source="site")
        self.sortant = Contact.objects.create(nom="Marc Vidal", organisation="Mairie de Gardanne", produit="vanessa",
                                              statut="lead", source="prospection", sens=Contact.Sens.SORTANT)

    def test_chaque_page_ne_montre_que_son_pipeline(self):
        entrants = self.client.get(reverse("contacts:liste"))
        self.assertEqual([c.nom for c in entrants.context["contacts"]], ["Claire Robin"])
        self.assertEqual(entrants.context["page"]["titre"], "Contacts entrants")
        sortants = self.client.get(reverse("contacts:sortants"))
        self.assertEqual([c.nom for c in sortants.context["contacts"]], ["Marc Vidal"])
        self.assertEqual(sortants.context["page"]["titre"], "Contacts sortants")

    def test_les_totaux_ne_melangent_pas_les_deux(self):
        page = self.client.get(reverse("contacts:sortants"))
        self.assertEqual(page.context["totaux"]["leads"], 1)
        self.assertEqual(sum(r["leads"] for r in page.context["resumes"]), 1)

    def test_la_prospection_va_droit_au_pipeline(self):
        """Sortants : ni tuiles de synthèse, ni cartes par logiciel — seulement les colonnes."""
        sortants = self.client.get(reverse("contacts:sortants"))
        self.assertNotContains(sortants, "Par logiciel")
        self.assertNotContains(sortants, "Leads en cours")
        self.assertContains(sortants, "Marc Vidal")
        entrants = self.client.get(reverse("contacts:liste"))
        self.assertContains(entrants, "Par logiciel")
        self.assertContains(entrants, "Leads en cours")

    def test_la_demande_du_site_arrive_en_entrant(self):
        DemandeDemonstration.objects.create(nom="Paul Nicolas", organisation="EARL Nicolas", courriel="paul@earl.fr",
                                            sujet="isidor", message="80 ha")
        self.assertEqual(Contact.objects.get(courriel="paul@earl.fr").sens, Contact.Sens.ENTRANT)

    def test_creation_depuis_la_page_sortants(self):
        depart = self.client.get(reverse("contacts:ajouter"), {"sens": "sortant"})
        self.assertEqual(depart.context["form"].initial["sens"], Contact.Sens.SORTANT)
        self.client.post(reverse("contacts:ajouter"), {
            "nom": "Léa Faure", "organisation": "Mairie d'Apt", "sens": "sortant", "produit": "vanessa",
            "statut": "lead", "source": "salon",
        })
        self.assertEqual(Contact.objects.get(nom="Léa Faure").sens, Contact.Sens.SORTANT)

    def test_le_csv_suit_le_pipeline_demande(self):
        contenu = self.client.get(reverse("contacts:export"), {"sens": "sortant"}).content.decode("utf-8-sig")
        self.assertIn("Marc Vidal", contenu)
        self.assertNotIn("Claire Robin", contenu)

    def test_la_fiche_renvoie_vers_son_pipeline(self):
        page = self.client.get(reverse("contacts:fiche", args=[self.sortant.pk]))
        self.assertEqual(page.context["url_liste"], reverse("contacts:sortants"))
        self.assertContains(page, "Contacts sortants")

    def test_le_menu_montre_les_deux_rubriques(self):
        page = self.client.get(reverse("contacts:sortants")).content.decode()
        self.assertIn("Contacts entrants", page)
        self.assertIn("Contacts sortants", page)
        # C'est la rubrique du pipeline affiché qui est marquée courante.
        lien = page.index(f'href="{reverse("contacts:sortants")}"')
        self.assertIn('aria-current="page"', page[lien:lien + 120])
        entrants = page.index(f'href="{reverse("contacts:liste")}"')
        self.assertNotIn('aria-current="page"', page[entrants:entrants + 120])

    def test_la_suppression_ramene_au_bon_pipeline(self):
        reponse = self.client.post(reverse("contacts:supprimer", args=[self.sortant.pk]))
        self.assertRedirects(reponse, reverse("contacts:sortants"))


class NoteEstimationTests(TestCase):
    """L'astérisque du potentiel n'est expliqué que lorsqu'une estimation est affichée."""

    def setUp(self):
        self.equipe = get_user_model().objects.create_user("equipe3", "e3@satkaar.io", "x", is_staff=True)
        self.client.force_login(self.equipe)

    def test_pas_de_note_sans_estimation(self):
        Contact.objects.create(nom="Claire Robin", produit="vanessa", statut="lead", montant=Decimal("4800"))
        self.assertNotContains(self.client.get(reverse("contacts:liste")), "Estimation Isidor")

    def test_note_affichee_avec_une_estimation(self):
        Contact.objects.create(nom="Yannick Pastre", produit="isidor", statut="lead", taille=120)
        self.assertContains(self.client.get(reverse("contacts:liste")), "Estimation Isidor")


class ImportMairiesTests(TestCase):
    """La commande verse un fichier de communes en contacts sortants, sans jamais dupliquer."""

    ENTETE = ("Code INSEE;Nom;Prénom;Ville;Code postal;Département;Code département;Région;Population;Âge;"
              "Date de naissance;Profession;Début du mandat;Courriel mairie;Téléphone mairie;Site internet;SIREN\n")
    LIGNES = (
        "38442;DURAND;Fabien;Saint-Savin;38300;Isère;38;Auvergne-Rhône-Alpes;4323;44;1982-04-02;Employé;"
        "2026-03-22;mairie@saint-savin38.fr;04 74 88 00 00;https://saint-savin38.fr;213804420\n"
        "33472;JOINT;Frédérique;Saint-Savin;33920;Gironde;33;Nouvelle-Aquitaine;3582;47;1979-01-15;Cadre;"
        "2026-03-22;mairie@saint-savin33.fr;05 57 58 00 00;;213304720\n"
        "13055;PAYAN;Benoît;Marseille;13001;Bouches-du-Rhône;13;Provence-Alpes-Côte d'Azur;886040;48;1978-06-11;"
        "Cadre;2026-03-22;;30 13;https://marseille.fr;211300553\n"
    )

    def setUp(self):
        self.fichier = Path(tempfile.mkdtemp()) / "communes.csv"
        self.fichier.write_text(self.ENTETE + self.LIGNES, encoding="utf-8-sig")
        self.addCleanup(shutil.rmtree, self.fichier.parent, ignore_errors=True)

    def importer(self, **options):
        sortie = StringIO()
        call_command("importer_mairies", str(self.fichier), stdout=sortie, **options)
        return sortie.getvalue()

    def test_les_communes_deviennent_des_contacts_sortants(self):
        self.importer()
        marseille = Contact.objects.get(ville="Marseille")
        self.assertEqual((marseille.nom, marseille.prenom, marseille.nom_complet), ("PAYAN", "Benoît", "Benoît PAYAN"))
        self.assertEqual((marseille.departement, marseille.region), ("Bouches-du-Rhône", "Provence-Alpes-Côte d'Azur"))
        self.assertEqual(marseille.age, 48)
        self.assertEqual((marseille.fonction, marseille.organisation), ("Maire", "Mairie de Marseille"))
        self.assertEqual((marseille.sens, marseille.produit, marseille.statut), ("sortant", "vanessa", "lead"))
        self.assertEqual((marseille.source, marseille.taille), ("prospection", 886040))
        # L'origine de la donnée est consignée dans un échange, pour savoir d'où sort la fiche.
        self.assertIn("Répertoire National des Élus", marseille.notes.get().texte)

    def test_les_homonymes_sont_distingues_par_le_departement(self):
        self.importer()
        self.assertEqual(
            sorted(Contact.objects.filter(ville="Saint-Savin").values_list("organisation", flat=True)),
            ["Mairie de Saint-Savin (Gironde)", "Mairie de Saint-Savin (Isère)"])

    def test_rejouable_sans_doublon(self):
        self.importer()
        self.importer()
        self.assertEqual(Contact.objects.count(), 3)
        self.assertEqual(Note.objects.count(), 3)

    def test_essai_n_ecrit_rien(self):
        sortie = self.importer(essai=True)
        self.assertEqual(Contact.objects.count(), 0)
        self.assertIn("3 à créer", sortie)

    def test_filtres(self):
        self.importer(population_min=4000)
        self.assertEqual(sorted(c.ville for c in Contact.objects.all()), ["Marseille", "Saint-Savin"])
        Contact.objects.all().delete()
        self.importer(departements="33", limite=5)
        self.assertEqual([c.taille for c in Contact.objects.all()], [3582])

    def test_fichier_introuvable(self):
        with self.assertRaises(CommandError):
            call_command("importer_mairies", "donnees/nexiste-pas.csv")


class TableauProspectionTests(TestCase):
    """Le tableau des sortants : colonnes, tri, pagination, étape modifiable sur place."""

    def setUp(self):
        self.equipe = get_user_model().objects.create_user("equipe4", "e4@satkaar.io", "x", is_staff=True)
        self.client.force_login(self.equipe)
        self.nantes = Contact.objects.create(
            nom="ROLLAND", prenom="Johanna", ville="Nantes", departement="Loire-Atlantique",
            region="Pays de la Loire", date_naissance=date(1979, 4, 25), taille=327734,
            courriel="contact@mairie-nantes.fr", produit="vanessa", sens="sortant", statut="lead", source="prospection")
        self.apt = Contact.objects.create(
            nom="FAURE", prenom="Léa", ville="Apt", departement="Vaucluse", region="Provence-Alpes-Côte d'Azur",
            date_naissance=date(1990, 1, 10), taille=11500, produit="vanessa", sens="sortant",
            statut="contacte", source="salon")

    def test_le_tableau_est_la_vue_par_defaut_avec_ses_colonnes(self):
        page = self.client.get(reverse("contacts:sortants"))
        self.assertEqual(page.context["vue"], "liste")
        for entete in ("Prénom", "Département", "Région", "Habitants", "Âge", "Contacté le", "Réponse le", "Courriel"):
            self.assertContains(page, entete)
        self.assertContains(page, "contact@mairie-nantes.fr")
        self.assertContains(page, "Johanna")

    def test_age_calcule_depuis_la_date_de_naissance(self):
        self.assertEqual(self.nantes.age, 47)
        self.assertEqual(self.apt.age, 36)
        self.assertIsNone(Contact(nom="X").age)

    def test_tri_par_colonne_et_inversion(self):
        page = self.client.get(reverse("contacts:sortants"), {"tri": "ville"})
        self.assertEqual([c.ville for c in page.context["contacts"]], ["Apt", "Nantes"])
        page = self.client.get(reverse("contacts:sortants"), {"tri": "-ville"})
        self.assertEqual([c.ville for c in page.context["contacts"]], ["Nantes", "Apt"])
        # Par défaut, les plus grandes communes d'abord.
        self.assertEqual([c.ville for c in self.client.get(reverse("contacts:sortants")).context["contacts"]],
                         ["Nantes", "Apt"])

    def test_tri_par_age(self):
        """Âge croissant : le plus jeune d'abord, quel que soit l'ordre des dates de naissance."""
        page = self.client.get(reverse("contacts:sortants"), {"tri": "age"})
        self.assertEqual([c.prenom for c in page.context["contacts"]], ["Léa", "Johanna"])
        page = self.client.get(reverse("contacts:sortants"), {"tri": "-age"})
        self.assertEqual([c.prenom for c in page.context["contacts"]], ["Johanna", "Léa"])

    def test_tri_inconnu_ignore(self):
        page = self.client.get(reverse("contacts:sortants"), {"tri": "courriel; DROP"})
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context["tri_cle"], "")

    def test_changer_l_etape_depuis_le_tableau_pose_les_dates(self):
        suivant = reverse("contacts:sortants") + "?vue=liste"
        reponse = self.client.post(reverse("contacts:etape", args=[self.nantes.pk]), {"statut": "contacte", "suivant": suivant})
        self.assertRedirects(reponse, suivant)
        self.nantes.refresh_from_db()
        self.assertEqual((self.nantes.statut, self.nantes.date_contact), ("contacte", timezone.localdate()))
        self.assertIsNone(self.nantes.date_reponse)
        # La réponse du prospect est datée au premier signe de retour.
        self.client.post(reverse("contacts:etape", args=[self.nantes.pk]), {"statut": "demo", "suivant": suivant})
        self.nantes.refresh_from_db()
        self.assertEqual(self.nantes.date_reponse, timezone.localdate())

    def test_les_dates_deja_saisies_ne_sont_pas_ecrasees(self):
        veille = timezone.localdate() - timedelta(days=30)
        Contact.objects.filter(pk=self.apt.pk).update(date_contact=veille)
        self.client.post(reverse("contacts:etape", args=[self.apt.pk]), {"statut": "demo"})
        self.apt.refresh_from_db()
        self.assertEqual(self.apt.date_contact, veille)

    def test_envoi_sans_etape_ne_casse_pas_la_page(self):
        """Le champ peut manquer (formulaire incomplet) : on le dit, sans page d'erreur."""
        suivant = reverse("contacts:sortants")
        reponse = self.client.post(reverse("contacts:etape", args=[self.nantes.pk]), {"suivant": suivant}, follow=True)
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Étape inconnue")
        self.nantes.refresh_from_db()
        self.assertEqual(self.nantes.statut, "lead")

    def test_retour_hors_du_site_ignore(self):
        reponse = self.client.post(reverse("contacts:etape", args=[self.nantes.pk]),
                                   {"statut": "demo", "suivant": "https://exemple.fr/piege"})
        self.assertRedirects(reponse, reverse("contacts:fiche", args=[self.nantes.pk]))

    def test_pagination(self):
        for numero in range(60):
            Contact.objects.create(nom=f"MAIRE{numero}", ville=f"Commune {numero}", produit="vanessa",
                                   sens="sortant", statut="lead", taille=3000 + numero)
        page = self.client.get(reverse("contacts:sortants"))
        self.assertEqual(len(page.context["contacts"]), 50)
        self.assertEqual(page.context["total"], 62)
        self.assertEqual(len(self.client.get(reverse("contacts:sortants"), {"page": 2}).context["contacts"]), 12)

    def test_le_csv_des_sortants_a_les_memes_colonnes(self):
        contenu = self.client.get(reverse("contacts:export"), {"sens": "sortant"}).content.decode("utf-8-sig")
        entete = contenu.splitlines()[0]
        self.assertEqual(entete.split(";")[:7], ["Nom", "Prénom", "Ville", "Département", "Région", "Habitants", "Âge"])
        self.assertIn("ROLLAND;Johanna;Nantes;Loire-Atlantique;Pays de la Loire;327734;47", contenu)
