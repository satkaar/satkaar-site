"""Verse un fichier de communes en contacts sortants Vanessa.

    python manage.py importer_mairies donnees/communes-3000-hab-maires-moins-50-ans.csv --essai
    python manage.py importer_mairies donnees/communes-3000-hab-maires-moins-50-ans.csv --population-min 5000

Le fichier vient du croisement Répertoire National des Élus × population INSEE. La commande
est rejouable : une commune déjà présente est mise à jour, jamais dupliquée.
"""

import csv
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from contacts.models import Contact, Note

COLONNES = ("Code INSEE", "Nom", "Prénom", "Ville", "Département", "Région", "Population", "Date de naissance")


class Command(BaseCommand):
    help = "Importe des communes (fichier CSV) comme contacts sortants à démarcher pour Vanessa."

    def add_arguments(self, parser):
        parser.add_argument("fichier", help="CSV séparé par des points-virgules.")
        parser.add_argument("--essai", action="store_true", help="Montrer ce qui serait fait, sans rien écrire.")
        parser.add_argument("--population-min", type=int, default=0, help="Ne garder que les communes au-dessus.")
        parser.add_argument("--population-max", type=int, default=0, help="Ne garder que les communes en dessous.")
        parser.add_argument("--age-max", type=int, default=0, help="Ne garder que les maires plus jeunes.")
        parser.add_argument("--departements", default="", help="Codes séparés par des virgules : 13,83,84.")
        parser.add_argument("--limite", type=int, default=0, help="S'arrêter après N communes.")

    def handle(self, *args, fichier, essai, population_min, population_max, age_max, departements, limite, **options):
        chemin = Path(fichier)
        if not chemin.exists():
            raise CommandError(f"Fichier introuvable : {chemin}")
        with chemin.open(encoding="utf-8-sig", newline="") as f:
            lignes = list(csv.DictReader(f, delimiter=";"))
        manquantes = [c for c in COLONNES if lignes and c not in lignes[0]]
        if manquantes:
            raise CommandError(f"Colonnes absentes du fichier : {', '.join(manquantes)}")

        codes = {d.strip() for d in departements.split(",") if d.strip()}
        retenues = []
        for ligne in lignes:
            population, age = int(ligne["Population"]), int(ligne["Âge"] or 0)
            if population < population_min or (population_max and population > population_max):
                continue
            if age_max and age >= age_max:
                continue
            if codes and ligne.get("Code département") not in codes:
                continue
            retenues.append(ligne)
            if limite and len(retenues) >= limite:
                break

        # Deux communes peuvent porter le même nom (Saint-Savin…) : on précise alors le
        # département, sans quoi la seconde écraserait la première à chaque import.
        homonymes = {n for n, k in Counter(l["Ville"] for l in retenues).items() if k > 1}

        crees, maj = 0, 0
        with transaction.atomic():
            for ligne in retenues:
                commune, departement = ligne["Ville"], ligne["Département"]
                organisation = f"Mairie de {commune}" + (f" ({departement})" if commune in homonymes else "")
                contact = Contact.objects.filter(produit=Contact.Produit.VANESSA, ville=commune,
                                                 organisation=organisation).first()
                valeurs = {
                    "nom": ligne["Nom"], "prenom": ligne["Prénom"], "fonction": "Maire",
                    "ville": commune, "departement": departement, "region": ligne.get("Région", ""),
                    "organisation": organisation, "produit": Contact.Produit.VANESSA,
                    "sens": Contact.Sens.SORTANT, "source": Contact.Source.PROSPECTION,
                    "taille": int(ligne["Population"]),
                    "date_naissance": ligne["Date de naissance"] or None,
                    "courriel": ligne.get("Courriel mairie", ""),
                    "telephone": ligne.get("Téléphone mairie", ""),
                }
                if contact:
                    for champ, valeur in valeurs.items():
                        setattr(contact, champ, valeur)
                    if not essai:
                        contact.save()
                    maj += 1
                    continue
                crees += 1
                if essai:
                    continue
                contact = Contact.objects.create(statut=Contact.Statut.LEAD, **valeurs)
                Note.objects.create(
                    contact=contact, type=Note.Type.NOTE,
                    texte=(f"Importé du croisement Répertoire National des Élus × population INSEE. "
                           f"{ligne['Prénom']} {ligne['Nom']}, {ligne['Âge']} ans"
                           + (f", {ligne['Profession'].lower()}" if ligne.get("Profession") else "")
                           + f". Mandat depuis le {ligne.get('Début du mandat', '?')}. "
                           f"{int(ligne['Population']):n} habitants · {departement} · INSEE {ligne['Code INSEE']}."
                           + (f" Site : {ligne['Site internet']}" if ligne.get("Site internet") else "")),
                )
            if essai:
                transaction.set_rollback(True)

        prefixe = "[essai] " if essai else ""
        self.stdout.write(f"{prefixe}{len(retenues)} commune(s) retenue(s) sur {len(lignes)} : "
                          f"{crees} à créer, {maj} déjà présente(s).")
