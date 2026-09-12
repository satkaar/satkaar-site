"""Calculs de l'agenda : éléments à afficher (événements et rappels demandés sur le site),
placement dans la grille de la semaine, grille du mois et export iCalendar."""

import calendar
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta

from django.urls import reverse
from django.utils import timezone

from pages.models import DemandeDemonstration

from .models import Evenement

HEURE_DEBUT, HEURE_FIN = 7, 21  # plage affichée dans la grille de la semaine
DUREE_MIN = 30  # minutes : un créneau plus court reste lisible

# Une couleur par catégorie ; la catégorie est toujours écrite à côté (légende, info-bulle, détail).
CATEGORIES = {
    "rendez_vous": ("Rendez-vous client", "#1e63a8"),
    "formation": ("Formation", "#2e6b5a"),
    "deploiement": ("Déploiement", "#be5620"),
    "interne": ("Interne", "#6b4fa0"),
    "autre": ("Autre", "#5c6672"),
    "rappel": ("Rappel demandé sur le site", "#0f7c8c"),
}


@dataclass
class Element:
    titre: str
    categorie: str
    debut: datetime
    fin: datetime
    url: str
    journee_entiere: bool = False
    lieu: str = ""
    visio: bool = False
    detail: str = ""
    fait: bool = False
    participants: list = field(default_factory=list)

    def __post_init__(self):
        # Heure de Paris : les gabarits lisent .date et .hour, qui resteraient sinon en UTC.
        self.debut, self.fin = timezone.localtime(self.debut), timezone.localtime(self.fin)

    @property
    def categorie_libelle(self):
        return CATEGORIES[self.categorie][0]

    @property
    def horaire(self):
        if self.journee_entiere:
            return "Journée entière"
        debut, fin = timezone.localtime(self.debut), timezone.localtime(self.fin)
        return f"{debut:%H:%M} – {fin:%H:%M}"


def _aware(jour, heure=time(0)):
    return timezone.make_aware(datetime.combine(jour, heure))


def elements(debut, fin):
    """Événements de l'équipe et rappels demandés via le formulaire de contact, entre deux instants."""
    trouves = [
        Element(
            titre=e.titre, categorie=e.categorie, debut=e.debut, fin=e.fin, journee_entiere=e.journee_entiere,
            url=reverse("agenda:evenement", args=[e.pk]), lieu=e.lieu, visio=bool(e.lien_visio), detail=e.organisation,
            participants=[p.get_full_name() or p.email for p in e.participants.all()],
        )
        for e in Evenement.objects.filter(debut__lt=fin, fin__gt=debut).prefetch_related("participants")
    ]
    demandes = DemandeDemonstration.objects.filter(
        rappel_jour__gte=timezone.localtime(debut).date(), rappel_jour__lte=timezone.localtime(fin).date())
    for d in demandes:
        commence = _aware(d.rappel_jour, d.rappel_heure or time(0))
        trouves.append(Element(
            titre=f"Rappeler {d.nom}", categorie="rappel", debut=commence,
            fin=commence + (timedelta(minutes=DUREE_MIN) if d.rappel_heure else timedelta(days=1)),
            journee_entiere=not d.rappel_heure, url=reverse("admin:pages_demandedemonstration_change", args=[d.pk]),
            detail=f"{d.organisation} · {d.telephone}" if d.telephone else d.organisation, fait=d.traitee,
        ))
    return sorted(trouves, key=lambda e: (not e.journee_entiere, e.debut))


def _placer(creneaux, debut_jour):
    """Positionne les créneaux (en % de la plage horaire) et répartit côte à côte ceux qui se chevauchent."""
    total = (HEURE_FIN - HEURE_DEBUT) * 60
    origine = debut_jour + timedelta(hours=HEURE_DEBUT)
    places = []
    for element, debut, fin in sorted(creneaux, key=lambda c: (c[1], c[2])):
        haut = min(max((debut - origine).total_seconds() / 60, 0), total - DUREE_MIN)
        duree = max((fin - debut).total_seconds() / 60, DUREE_MIN)
        bas = min(haut + duree, total)
        places.append({"element": element, "haut": haut, "bas": bas, "voie": 0, "voies": 1,
                       "debut": timezone.localtime(debut), "fin": timezone.localtime(fin)})

    groupe, fin_groupe = [], -1
    for place in places + [None]:
        if place is None or place["haut"] >= fin_groupe:
            voies_du_groupe = max((p["voie"] for p in groupe), default=0) + 1
            for p in groupe:
                p["voies"] = voies_du_groupe
            if place is None:
                break
            groupe, fin_groupe = [], -1
        occupees = {p["voie"] for p in groupe if p["bas"] > place["haut"]}
        place["voie"] = next(v for v in range(len(groupe) + 1) if v not in occupees)
        groupe.append(place)
        fin_groupe = max(fin_groupe, place["bas"])

    for p in places:
        p["haut_pct"] = round(p["haut"] / total * 100, 3)
        p["hauteur_pct"] = round((p["bas"] - p["haut"]) / total * 100, 3)
        p["gauche_pct"] = round(p["voie"] / p["voies"] * 100, 3)
        p["largeur_pct"] = round(100 / p["voies"], 3)
    return places


def semaine(lundi, trouves, maintenant):
    jours = []
    for i in range(7):
        jour = lundi + timedelta(days=i)
        debut_jour, fin_jour = _aware(jour), _aware(jour + timedelta(days=1))
        journee, creneaux = [], []
        for e in trouves:
            if e.fin <= debut_jour or e.debut >= fin_jour:
                continue
            if e.journee_entiere or (e.debut <= debut_jour and e.fin >= fin_jour):
                journee.append(e)
            else:
                creneaux.append((e, max(e.debut, debut_jour), min(e.fin, fin_jour)))
        maintenant_local = timezone.localtime(maintenant)
        repere = None
        if jour == maintenant_local.date() and HEURE_DEBUT <= maintenant_local.hour < HEURE_FIN:
            minutes = (maintenant_local.hour - HEURE_DEBUT) * 60 + maintenant_local.minute
            repere = round(minutes / ((HEURE_FIN - HEURE_DEBUT) * 60) * 100, 3)
        jours.append({"date": jour, "aujourdhui": jour == maintenant_local.date(), "journee": journee,
                      "placements": _placer(creneaux, debut_jour), "repere": repere})
    return jours


def grille_mois(annee, mois, trouves=(), aujourdhui=None, semaine_de=None):
    """Semaines du mois (lundi → dimanche) avec, pour chaque jour, ses éléments."""
    semaines = []
    for sem in calendar.Calendar(firstweekday=0).monthdatescalendar(annee, mois):
        ligne = []
        for jour in sem:
            debut_jour, fin_jour = _aware(jour), _aware(jour + timedelta(days=1))
            du_jour = [e for e in trouves if e.debut < fin_jour and e.fin > debut_jour]
            ligne.append({
                "date": jour, "hors_mois": jour.month != mois, "aujourdhui": jour == aujourdhui,
                "elements": du_jour, "dans_semaine": bool(semaine_de) and semaine_de <= jour < semaine_de + timedelta(days=7),
            })
        semaines.append(ligne)
    return semaines


def lundi_de(jour):
    return jour - timedelta(days=jour.weekday())


def mois_voisins(annee, mois):
    precedent = date(annee - 1, 12, 1) if mois == 1 else date(annee, mois - 1, 1)
    suivant = date(annee + 1, 1, 1) if mois == 12 else date(annee, mois + 1, 1)
    return precedent, suivant


# --- iCalendar -------------------------------------------------------------------------------

def _echapper(texte):
    return (texte or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n")


def _plier(ligne):
    """Lignes de 75 octets au plus, les suivantes commençant par une espace (RFC 5545)."""
    octets, morceaux = ligne.encode(), []
    while len(octets) > 75:
        coupe = 75 if not morceaux else 74
        while (octets[coupe] & 0xC0) == 0x80:  # ne pas couper un caractère UTF-8 en deux
            coupe -= 1
        morceaux.append(octets[:coupe])
        octets = octets[coupe:]
    morceaux.append(octets)
    return b"\r\n ".join(morceaux).decode()


def _utc(moment):
    return moment.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def ics(evenement, domaine="satkaar.io"):
    if evenement.journee_entiere:
        dates = [f"DTSTART;VALUE=DATE:{timezone.localtime(evenement.debut):%Y%m%d}",
                 f"DTEND;VALUE=DATE:{timezone.localtime(evenement.fin):%Y%m%d}"]
    else:
        dates = [f"DTSTART:{_utc(evenement.debut)}", f"DTEND:{_utc(evenement.fin)}"]
    description = "\n\n".join(filter(None, [evenement.description, f"Visio : {evenement.lien_visio}" if evenement.lien_visio else ""]))
    lignes = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Satkaar//Agenda//FR", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        "BEGIN:VEVENT", f"UID:agenda-{evenement.pk}@{domaine}", f"DTSTAMP:{_utc(timezone.now())}", *dates,
        f"SUMMARY:{_echapper(evenement.titre)}",
    ]
    if evenement.lieu or evenement.lien_visio:
        lignes.append(f"LOCATION:{_echapper(evenement.lieu or evenement.lien_visio)}")
    if description:
        lignes.append(f"DESCRIPTION:{_echapper(description)}")
    if evenement.lien_visio:
        lignes.append(f"URL:{evenement.lien_visio}")
    lignes += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(_plier(l) for l in lignes) + "\r\n"
