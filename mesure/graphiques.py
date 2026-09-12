"""Géométrie des graphiques, calculée côté serveur et dessinée en SVG dans le gabarit."""

import math

MOIS_COURTS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def graduations(maximum, cible=4):
    """Graduations « rondes » (1, 2, 5 × 10^n) de 0 jusqu'au-dessus du maximum."""
    if maximum <= 0:
        return [0, 1]
    brut = maximum / cible
    puissance = 10 ** math.floor(math.log10(brut))
    pas = next(p * puissance for p in (1, 2, 5, 10) if p * puissance >= brut)
    pas = max(pas, 1)
    haut = pas * math.ceil(maximum / pas)
    return [round(i * pas) for i in range(int(haut / pas) + 1)]


def courbe(serie, cle, largeur=720, hauteur=240, marge_g=40, marge_b=28, marge_h=12, marge_d=12):
    valeurs = [p[cle] for p in serie]
    ticks = graduations(max(valeurs, default=0))
    haut = ticks[-1] or 1
    zone_l, zone_h = largeur - marge_g - marge_d, hauteur - marge_h - marge_b
    n = len(valeurs)

    def x(i):
        return marge_g + (zone_l * i / (n - 1) if n > 1 else zone_l / 2)

    def y(v):
        return marge_h + zone_h * (1 - v / haut)

    points = [(round(x(i), 1), round(y(v), 1)) for i, v in enumerate(valeurs)]
    trace = "M" + " L".join(f"{px} {py}" for px, py in points) if points else ""
    base = round(y(0), 1)
    aire = f"{trace} L{points[-1][0]} {base} L{points[0][0]} {base} Z" if points else ""
    pas_etiquettes = max(1, math.ceil(n / 6))
    return {
        "largeur": largeur, "hauteur": hauteur, "trace": trace, "aire": aire,
        "gauche": marge_g, "droite": largeur - marge_d, "base": base,
        "graduations": [{"valeur": t, "y": round(y(t), 1)} for t in ticks],
        "etiquettes": [
            {"x": points[i][0], "texte": f"{serie[i]['jour'].day} {MOIS_COURTS[serie[i]['jour'].month - 1]}"}
            for i in range(0, n, pas_etiquettes)
        ],
        "points": [
            {"x": px, "y": py, "valeur": valeurs[i],
             "texte": f"{serie[i]['jour'].day} {MOIS_COURTS[serie[i]['jour'].month - 1]}"}
            for i, (px, py) in enumerate(points)
        ],
        "dernier": {"x": points[-1][0], "y": points[-1][1], "valeur": valeurs[-1]} if points else None,
        "pas": round(zone_l / (n - 1), 1) if n > 1 else zone_l,
    }


def colonnes(lignes, largeur=720, hauteur=200, marge_g=40, marge_b=28, marge_h=12, marge_d=8, epaisseur_max=24):
    valeurs = [l["nombre"] for l in lignes]
    ticks = graduations(max(valeurs, default=0))
    haut = ticks[-1] or 1
    zone_l, zone_h = largeur - marge_g - marge_d, hauteur - marge_h - marge_b
    n = len(lignes)
    bande = zone_l / n
    epaisseur = min(epaisseur_max, bande * 0.6)
    base = marge_h + zone_h
    barres = []
    pas_etiquettes = 3 if n > 12 else 1
    for i, ligne in enumerate(lignes):
        h = zone_h * ligne["nombre"] / haut
        x0 = marge_g + bande * i + (bande - epaisseur) / 2
        rayon = min(4, h, epaisseur / 2)
        # Bout arrondi de 4 px en haut, pied carré sur la ligne de base.
        chemin = (
            f"M{x0:.1f} {base:.1f} V{base - h + rayon:.1f} "
            f"Q{x0:.1f} {base - h:.1f} {x0 + rayon:.1f} {base - h:.1f} "
            f"H{x0 + epaisseur - rayon:.1f} "
            f"Q{x0 + epaisseur:.1f} {base - h:.1f} {x0 + epaisseur:.1f} {base - h + rayon:.1f} "
            f"V{base:.1f} Z"
        ) if h > 0 else ""
        barres.append({
            "chemin": chemin, "libelle": ligne["libelle"], "valeur": ligne["nombre"],
            "centre": round(x0 + epaisseur / 2, 1),
            "zone_x": round(marge_g + bande * i, 1), "zone_l": round(bande, 1),
            "etiquette": (i % pas_etiquettes == 0),
            # « 12 h » reste entier, « Lundi » devient « Lun ».
            "court": ligne["libelle"] if len(ligne["libelle"]) <= 4 else ligne["libelle"][:3],
        })
    return {
        "largeur": largeur, "hauteur": hauteur, "gauche": marge_g, "droite": largeur - marge_d,
        "base": round(base, 1), "haut_zone": marge_h, "hauteur_zone": round(zone_h, 1),
        "graduations": [{"valeur": t, "y": round(marge_h + zone_h * (1 - t / haut), 1)} for t in ticks],
        "barres": barres,
    }


def mini_courbe(valeurs, largeur=120, hauteur=32):
    """Courbe miniature des tuiles d'indicateurs (12 derniers points)."""
    valeurs = valeurs[-12:]
    if len(valeurs) < 2:
        return None
    haut = max(valeurs) or 1
    pas = largeur / (len(valeurs) - 1)
    points = [(round(i * pas, 1), round(hauteur - 3 - (hauteur - 6) * v / haut, 1)) for i, v in enumerate(valeurs)]
    return {
        "trace": "M" + " L".join(f"{x} {y}" for x, y in points),
        "dernier": points[-1], "largeur": largeur, "hauteur": hauteur,
    }
