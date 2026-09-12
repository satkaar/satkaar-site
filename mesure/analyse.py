"""Calcul des indicateurs d'audience pour une période, et comparaison avec la précédente.

Les visites sont reconstituées à partir des pages vues : une visite s'arrête après 30 minutes
sans activité du même visiteur.
"""

import datetime
import statistics
from collections import Counter, defaultdict

from django.db.models import Q
from django.utils import timezone

from pages.models import DemandeDemonstration

from .models import Evenement, Mesure, PageVue, PassageRobot

PAUSE_VISITE = datetime.timedelta(minutes=30)
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
SOURCES = dict(PageVue.Source.choices)

# Seuils Google (valeur au 75e centile) : (bon jusqu'à, à améliorer jusqu'à, unité).
SEUILS_WEB_VITALS = {
    "lcp_ms": ("Affichage du contenu principal (LCP)", 2500, 4000, "ms"),
    "inp_ms": ("Réactivité aux interactions (INP)", 200, 500, "ms"),
    "cls": ("Stabilité visuelle (CLS)", 0.1, 0.25, ""),
    "fcp_ms": ("Premier affichage (FCP)", 1800, 3000, "ms"),
    "ttfb_ms": ("Temps de réponse du serveur (TTFB)", 800, 1800, "ms"),
}


def _pct(partie, total):
    return round(100 * partie / total, 1) if total else 0


def _variation(actuel, precedent):
    if not precedent:
        return None
    return round(100 * (actuel - precedent) / precedent, 1)


def _centile(valeurs, rang=75):
    valeurs = sorted(v for v in valeurs if v is not None)
    if not valeurs:
        return None
    if len(valeurs) == 1:
        return valeurs[0]
    return statistics.quantiles(valeurs, n=100, method="inclusive")[rang - 1]


def _repartition(compteur, total=None, limite=None):
    total = total if total is not None else sum(compteur.values())
    lignes = [{"libelle": cle or "Inconnu", "nombre": n, "part": _pct(n, total)}
              for cle, n in compteur.most_common(limite)]
    maximum = max((l["nombre"] for l in lignes), default=0)
    for ligne in lignes:
        ligne["largeur"] = round(100 * ligne["nombre"] / maximum, 1) if maximum else 0
    return lignes


def _visites(vues):
    """Regroupe les pages vues (triées par date) en visites."""
    par_visiteur = defaultdict(list)
    for vue in vues:
        par_visiteur[vue["visiteur"]].append(vue)
    visites = []
    for pages in par_visiteur.values():
        courante = [pages[0]]
        for vue in pages[1:]:
            if vue["horodatage"] - courante[-1]["horodatage"] > PAUSE_VISITE:
                visites.append(courante)
                courante = [vue]
            else:
                courante.append(vue)
        visites.append(courante)
    return visites


def _duree_visite(visite, mesures_du_visiteur):
    debut, fin = visite[0]["horodatage"], visite[-1]["horodatage"] + PAUSE_VISITE
    actif = sum(m["temps_actif_s"] for m in mesures_du_visiteur if debut <= m["horodatage"] <= fin)
    ecart = (visite[-1]["horodatage"] - visite[0]["horodatage"]).total_seconds()
    return max(actif, ecart)


def _chiffres_cles(debut, fin):
    vues = list(
        PageVue.objects.filter(horodatage__gte=debut, horodatage__lt=fin)
        .values("horodatage", "visiteur", "chemin", "statut", "source", "referent", "utm_source",
                "utm_medium", "utm_campagne", "appareil", "navigateur", "systeme", "langue",
                "duree_serveur_ms")
        .order_by("horodatage")
    )
    mesures = list(
        Mesure.objects.filter(horodatage__gte=debut, horodatage__lt=fin + PAUSE_VISITE)
        .values("horodatage", "visiteur", "chemin", "temps_actif_s", "defilement",
                "lcp_ms", "cls", "inp_ms", "fcp_ms", "ttfb_ms")
    )
    visites = _visites(vues)
    mesures_par_visiteur = defaultdict(list)
    for m in mesures:
        mesures_par_visiteur[m["visiteur"]].append(m)
    durees = [_duree_visite(v, mesures_par_visiteur[v[0]["visiteur"]]) for v in visites]
    demandes = DemandeDemonstration.objects.filter(cree_le__gte=debut, cree_le__lt=fin).count()
    nb_visites = len(visites)
    return {
        "vues": vues,
        "mesures": mesures,
        "visites": visites,
        "durees": durees,
        "kpi": {
            "visiteurs": len({v["visiteur"] for v in vues}),
            "visites": nb_visites,
            "pages_vues": sum(1 for v in vues if v["statut"] == 200),
            "pages_par_visite": round(len(vues) / nb_visites, 2) if nb_visites else 0,
            "duree_moyenne": round(sum(durees) / len(durees)) if durees else 0,
            "taux_rebond": _pct(sum(1 for v in visites if len(v) == 1), nb_visites),
            "demandes": demandes,
            "taux_conversion": _pct(demandes, nb_visites),
        },
    }


def _serie_par_jour(vues, visites, debut, jours):
    local = timezone.localtime
    visites_par_jour = Counter(local(v[0]["horodatage"]).date() for v in visites)
    vues_par_jour = Counter(local(v["horodatage"]).date() for v in vues)
    visiteurs_par_jour = defaultdict(set)
    for v in vues:
        visiteurs_par_jour[local(v["horodatage"]).date()].add(v["visiteur"])
    premier = local(debut).date()
    serie = []
    for i in range(jours):
        jour = premier + datetime.timedelta(days=i + 1)
        serie.append({
            "jour": jour,
            "visites": visites_par_jour.get(jour, 0),
            "pages_vues": vues_par_jour.get(jour, 0),
            "visiteurs": len(visiteurs_par_jour.get(jour, ())),
        })
    return serie


def analyser(jours=30, maintenant=None):
    maintenant = maintenant or timezone.now()
    fin = maintenant
    debut = fin - datetime.timedelta(days=jours)
    actuel = _chiffres_cles(debut, fin)
    precedent = _chiffres_cles(debut - datetime.timedelta(days=jours), debut)

    vues, visites, mesures = actuel["vues"], actuel["visites"], actuel["mesures"]
    local = timezone.localtime

    # Chiffres clés et évolution.
    kpi = []
    definitions = [
        ("visiteurs", "Visiteurs", "", True, "Empreintes distinctes, comptées par jour."),
        ("visites", "Visites", "", True, "Une visite s'arrête après 30 minutes sans activité."),
        ("pages_vues", "Pages vues", "", True, ""),
        ("pages_par_visite", "Pages par visite", "", True, ""),
        ("duree_moyenne", "Durée moyenne d'une visite", "s", True, "Temps passé actif sur le site."),
        ("taux_rebond", "Taux de rebond", "%", False, "Visites d'une seule page."),
        ("demandes", "Demandes de contact", "", True, "Formulaires envoyés."),
        ("taux_conversion", "Taux de conversion", "%", True, "Demandes de contact pour 100 visites."),
    ]
    for cle, libelle, unite, hausse_positive, aide in definitions:
        valeur, avant = actuel["kpi"][cle], precedent["kpi"][cle]
        variation = _variation(valeur, avant)
        kpi.append({
            "cle": cle, "libelle": libelle, "valeur": valeur, "unite": unite, "aide": aide,
            "precedent": avant, "variation": variation,
            "favorable": None if variation in (None, 0) else (variation > 0) == hausse_positive,
        })

    serie = _serie_par_jour(vues, visites, debut, jours)

    # Moments de visite.
    heures = Counter(local(v[0]["horodatage"]).hour for v in visites)
    jours_semaine = Counter(local(v[0]["horodatage"]).weekday() for v in visites)

    # Sources (première page de chaque visite ; une visite commencée « en interne » compte en direct).
    entrees = [v[0] for v in visites]
    sources = Counter(SOURCES["direct"] if e["source"] == "interne" else SOURCES[e["source"]] for e in entrees)
    par_source = defaultdict(Counter)
    for e in entrees:
        if e["referent"]:
            par_source[e["source"]][e["referent"]] += 1
    campagnes = Counter(
        " · ".join(x for x in (e["utm_source"], e["utm_medium"], e["utm_campagne"]) if x)
        for e in entrees if e["utm_source"]
    )

    # Pages.
    vues_200 = [v for v in vues if v["statut"] == 200]
    par_page = defaultdict(lambda: {"vues": 0, "visiteurs": set()})
    for v in vues_200:
        par_page[v["chemin"]]["vues"] += 1
        par_page[v["chemin"]]["visiteurs"].add(v["visiteur"])
    mesures_par_page = defaultdict(list)
    for m in mesures:
        mesures_par_page[m["chemin"]].append(m)
    sorties = Counter(v[-1]["chemin"] for v in visites)
    pages = []
    for chemin, d in sorted(par_page.items(), key=lambda x: -x[1]["vues"]):
        ms = mesures_par_page.get(chemin, [])
        pages.append({
            "chemin": chemin, "vues": d["vues"], "visiteurs": len(d["visiteurs"]),
            "temps_actif": round(sum(m["temps_actif_s"] for m in ms) / len(ms)) if ms else None,
            "defilement": round(sum(m["defilement"] for m in ms) / len(ms)) if ms else None,
            "sorties": sorties.get(chemin, 0),
            "taux_sortie": _pct(sorties.get(chemin, 0), d["vues"]),
        })

    # Engagement.
    engagement = {
        "temps_actif_moyen": round(sum(m["temps_actif_s"] for m in mesures) / len(mesures)) if mesures else 0,
        "defilement_moyen": round(sum(m["defilement"] for m in mesures) / len(mesures)) if mesures else 0,
        "lecture_complete": _pct(sum(1 for m in mesures if m["defilement"] >= 75), len(mesures)),
        "echantillons": len(mesures),
    }

    # Événements et conversions.
    evenements = Evenement.objects.filter(horodatage__gte=debut, horodatage__lt=fin)
    types = dict(Evenement.Type.choices)
    compte_evenements = Counter(evenements.values_list("type", flat=True))
    detail_evenements = defaultdict(Counter)
    for type_, cible in evenements.exclude(cible="").values_list("type", "cible"):
        detail_evenements[type_][cible] += 1
    demandes = DemandeDemonstration.objects.filter(cree_le__gte=debut, cree_le__lt=fin)
    sujets = dict(DemandeDemonstration.Sujet.choices)
    conversions = {
        "demandes": demandes.count(),
        "rappels": demandes.filter(Q(rappel_jour__isnull=False) | Q(rappel_heure__isnull=False)).count(),
        "par_sujet": _repartition(Counter(sujets.get(s, s) for s in demandes.values_list("sujet", flat=True))),
        "evenements": [{"libelle": types[t], "nombre": compte_evenements.get(t, 0)}
                       for t in types if t != Evenement.Type.TELECHARGEMENT],
        "sortants": _repartition(detail_evenements["sortant"], limite=10),
        "faq": _repartition(detail_evenements["faq"], limite=10),
        "appels_action": _repartition(detail_evenements["appel_action"], limite=10),
    }

    # Robots.
    robots = PassageRobot.objects.filter(horodatage__gte=debut, horodatage__lt=fin)
    familles = dict(PassageRobot.Famille.choices)
    par_robot = {}
    for nom, famille, date in robots.values_list("robot", "famille", "horodatage"):
        ligne = par_robot.setdefault(nom, {"robot": nom, "famille": familles[famille], "passages": 0, "dernier": date})
        ligne["passages"] += 1
        ligne["dernier"] = max(ligne["dernier"], date)
    robots_ia = robots.filter(famille="ia")
    robots_detail = {
        "total": robots.count(),
        "par_famille": _repartition(Counter(familles[f] for f in robots.values_list("famille", flat=True))),
        "liste": sorted(par_robot.values(), key=lambda r: -r["passages"]),
        "pages_ia": _repartition(Counter(robots_ia.values_list("chemin", flat=True)), limite=10),
        "fichiers": {f: robots.filter(chemin=f).count() for f in ("/robots.txt", "/llms.txt", "/sitemap.xml")},
    }

    # Performance.
    web_vitals = []
    for champ, (libelle, bon, moyen, unite) in SEUILS_WEB_VITALS.items():
        valeur = _centile([m[champ] for m in mesures])
        if valeur is None:
            statut = None
        elif valeur <= bon:
            statut = "bon"
        elif valeur <= moyen:
            statut = "moyen"
        else:
            statut = "mauvais"
        web_vitals.append({
            "libelle": libelle, "valeur": valeur, "unite": unite, "statut": statut,
            "bon": bon, "moyen": moyen,
            "echantillons": sum(1 for m in mesures if m[champ] is not None),
        })
    durees_serveur = [v["duree_serveur_ms"] for v in vues]
    serveur = {
        "moyenne": round(sum(durees_serveur) / len(durees_serveur)) if durees_serveur else None,
        "p95": round(_centile(durees_serveur, 95)) if durees_serveur else None,
    }

    return {
        "jours": jours,
        "debut": debut,
        "fin": fin,
        "kpi": kpi,
        "serie": serie,
        "temps_reel": PageVue.objects.filter(horodatage__gte=maintenant - datetime.timedelta(minutes=5))
        .values("visiteur").distinct().count(),
        "heures": [{"libelle": f"{h} h", "nombre": heures.get(h, 0)} for h in range(24)],
        "jours_semaine": [{"libelle": JOURS[j], "nombre": jours_semaine.get(j, 0)} for j in range(7)],
        "sources": _repartition(sources),
        "referents": _repartition(Counter(e["referent"] for e in entrees if e["referent"]), limite=10),
        "assistants_ia": _repartition(par_source["ia"]),
        "moteurs": _repartition(par_source["moteur"]),
        "reseaux": _repartition(par_source["social"]),
        "campagnes": _repartition(campagnes, limite=10),
        "pages": pages[:15],
        "entrees": _repartition(Counter(e["chemin"] for e in entrees), limite=10),
        "sorties": _repartition(sorties, limite=10),
        "erreurs_404": _repartition(Counter(v["chemin"] for v in vues if v["statut"] == 404), limite=10),
        "appareils": _repartition(Counter(e["appareil"] for e in entrees)),
        "navigateurs": _repartition(Counter(e["navigateur"] for e in entrees)),
        "systemes": _repartition(Counter(e["systeme"] for e in entrees)),
        "langues": _repartition(Counter(e["langue"] for e in entrees), limite=8),
        "engagement": engagement,
        "conversions": conversions,
        "robots": robots_detail,
        "web_vitals": web_vitals,
        "serveur": serveur,
    }
