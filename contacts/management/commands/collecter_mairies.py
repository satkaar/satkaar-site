"""Reconstruit le fichier des communes à démarcher, depuis trois sources publiques.

    python manage.py collecter_mairies --sortie donnees/communes.csv --population-min 3000 --age-max 50

Sources (Licence Ouverte) :
  - Répertoire National des Élus, fichier des maires (ministère de l'Intérieur) : identité et
    date de naissance ;
  - API Géo (geo.api.gouv.fr) : population légale INSEE, département, région ;
  - Annuaire de l'administration (service-public.fr) : courriel, téléphone et site de la mairie.

Le fichier produit contient des données personnelles d'élus : il reste hors du dépôt
(voir .gitignore), et c'est cette commande qui le régénère.
"""

import csv
import json
import urllib.request
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

RNE_MAIRES = "https://www.data.gouv.fr/api/1/datasets/5c34c4d1634f4173183a64f1/"
COMMUNES = "https://geo.api.gouv.fr/communes?fields=nom,code,population,codeDepartement,codeRegion,codesPostaux,siren"
DEPARTEMENTS = "https://geo.api.gouv.fr/departements"
REGIONS = "https://geo.api.gouv.fr/regions"
ANNUAIRE = ("https://api-lannuaire.service-public.fr/api/explore/v2.1/catalog/datasets/"
            "api-lannuaire-administration/exports/json?where=pivot%20like%20%22mairie%22"
            "&select=code_insee_commune,adresse_courriel,telephone,site_internet")
DELAI = 300


def _lire(url, binaire=False):
    with urllib.request.urlopen(url, timeout=DELAI) as reponse:  # noqa: S310 — adresses fixes ci-dessus
        contenu = reponse.read()
    return contenu if binaire else json.loads(contenu)


def _premier(brut, cle="valeur"):
    """Les champs de l'annuaire sont des listes JSON : on garde la première valeur."""
    if not brut:
        return ""
    try:
        valeurs = json.loads(brut) if isinstance(brut, str) else brut
    except json.JSONDecodeError:
        return ""
    return (valeurs[0].get(cle, "") if valeurs else "") if isinstance(valeurs, list) else ""


def _age(naissance, jour):
    n = date.fromisoformat(naissance)
    return jour.year - n.year - ((jour.month, jour.day) < (n.month, n.day))


class Command(BaseCommand):
    help = "Construit le CSV des communes à démarcher (population, maire, âge, contacts de la mairie)."

    def add_arguments(self, parser):
        parser.add_argument("--sortie", default="donnees/communes-a-demarcher.csv")
        parser.add_argument("--population-min", type=int, default=3000)
        parser.add_argument("--age-max", type=int, default=50)

    def handle(self, *args, sortie, population_min, age_max, **options):
        jour = timezone.localdate()
        self.stdout.write("Téléchargement des sources…")
        jeu = _lire(RNE_MAIRES)
        adresse = next((r["url"] for r in jeu["resources"] if "maire" in r["title"]), None)
        if not adresse:
            raise CommandError("Fichier des maires introuvable dans le Répertoire National des Élus.")
        maires = list(csv.DictReader(_lire(adresse, binaire=True).decode("utf-8").splitlines(), delimiter=";"))
        communes = {c["code"]: c for c in _lire(COMMUNES)}
        departements = {d["code"]: d["nom"] for d in _lire(DEPARTEMENTS)}
        regions = {r["code"]: r["nom"] for r in _lire(REGIONS)}
        annuaire = {}
        for mairie in _lire(ANNUAIRE):
            code = mairie.get("code_insee_commune")
            if code and code not in annuaire:
                annuaire[code] = mairie
        self.stdout.write(f"{len(maires)} maires · {len(communes)} communes · {len(annuaire)} mairies à l'annuaire")

        lignes = []
        for maire in maires:
            commune = communes.get(maire["Code de la commune"])
            naissance = maire["Date de naissance"]
            if not commune or (commune.get("population") or 0) <= population_min or not naissance:
                continue
            age = _age(naissance, jour)
            if age >= age_max:
                continue
            mairie = annuaire.get(commune["code"], {})
            lignes.append({
                "Code INSEE": commune["code"],
                "Nom": maire["Nom de l'élu"],
                "Prénom": maire["Prénom de l'élu"],
                "Ville": commune["nom"],
                "Code postal": (commune.get("codesPostaux") or [""])[0],
                # L'outre-mer (Nouvelle-Calédonie, Polynésie…) n'est pas dans la liste des
                # départements : le RNE le nomme comme collectivité à statut particulier.
                "Département": (departements.get(commune["codeDepartement"]) or maire["Libellé du département"]
                                or maire["Libellé de la collectivité à statut particulier"]),
                "Code département": commune["codeDepartement"],
                "Région": regions.get(commune["codeRegion"], ""),
                "Population": commune["population"],
                "Âge": age,
                "Date de naissance": naissance,
                "Profession": maire["Libellé de la catégorie socio-professionnelle"],
                "Début du mandat": maire["Date de début du mandat"],
                "Courriel mairie": mairie.get("adresse_courriel") or "",
                "Téléphone mairie": _premier(mairie.get("telephone")),
                "Site internet": _premier(mairie.get("site_internet")),
                "SIREN": commune.get("siren", ""),
            })

        if not lignes:
            raise CommandError("Aucune commune ne correspond à ces critères.")
        lignes.sort(key=lambda l: (-l["Population"], l["Ville"]))
        chemin = Path(sortie)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with chemin.open("w", encoding="utf-8-sig", newline="") as f:
            ecrivain = csv.DictWriter(f, fieldnames=list(lignes[0]), delimiter=";")
            ecrivain.writeheader()
            ecrivain.writerows(lignes)
        avec_courriel = sum(1 for l in lignes if l["Courriel mairie"])
        self.stdout.write(f"{len(lignes)} commune(s) de plus de {population_min} habitants avec un maire de moins "
                          f"de {age_max} ans → {chemin} ({avec_courriel} avec un courriel).")
