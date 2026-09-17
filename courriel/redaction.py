"""Corps HTML d'un message écrit dans l'espace : nettoyage et version texte.

Le HTML vient d'un éditeur du navigateur : on ne renvoie au destinataire que des balises de
mise en forme, jamais de script ni de gestionnaire d'événement.
"""

import re
from html import unescape
from html.parser import HTMLParser

BALISES_AUTORISEES = {
    "p", "br", "div", "span", "b", "strong", "i", "em", "u", "s", "strike", "sub", "sup",
    "ul", "ol", "li", "blockquote", "pre", "code", "a", "img", "h1", "h2", "h3", "h4",
    "table", "thead", "tbody", "tr", "td", "th", "hr",
}
ATTRIBUTS_AUTORISES = {"href", "src", "alt", "title", "style", "colspan", "rowspan"}
# Mise en forme seulement : ni position, ni comportement.
STYLES_AUTORISES = ("color", "background-color", "font-weight", "font-style", "text-decoration",
                    "text-align", "font-size", "font-family", "margin", "padding", "border-left")
BALISES_VIDES = {"br", "img", "hr"}


class _Nettoyeur(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.morceaux = []
        self.ignore = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "iframe", "object", "embed"):
            self.ignore += 1
            return
        if self.ignore or tag not in BALISES_AUTORISEES:
            return
        propres = []
        for nom, valeur in attrs:
            nom, valeur = nom.lower(), (valeur or "").strip()
            if nom not in ATTRIBUTS_AUTORISES or nom.startswith("on"):
                continue
            if nom in ("href", "src"):
                if valeur.lower().startswith(("javascript:", "data:text", "vbscript:")):
                    continue
            if nom == "style":
                valeur = ";".join(d for d in valeur.split(";")
                                  if d.split(":")[0].strip().lower() in STYLES_AUTORISES)
                if not valeur:
                    continue
            propres.append(f'{nom}="{valeur}"')
        self.morceaux.append(f"<{tag}{' ' + ' '.join(propres) if propres else ''}>")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "iframe", "object", "embed"):
            self.ignore = max(0, self.ignore - 1)
            return
        if not self.ignore and tag in BALISES_AUTORISEES and tag not in BALISES_VIDES:
            self.morceaux.append(f"</{tag}>")

    def handle_data(self, donnees):
        if not self.ignore:
            self.morceaux.append(donnees.replace("<", "&lt;").replace(">", "&gt;"))


def nettoyer(html):
    """HTML débarrassé de tout ce qui n'est pas de la mise en forme."""
    if not (html or "").strip():
        return ""
    nettoyeur = _Nettoyeur()
    nettoyeur.feed(html)
    nettoyeur.close()
    return "".join(nettoyeur.morceaux).strip()


def en_texte(html):
    """Version texte d'un corps HTML, pour les logiciels qui n'affichent pas le HTML."""
    texte = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html or "")
    texte = re.sub(r"(?i)<br\s*/?>", "\n", texte)
    texte = re.sub(r"(?i)</(p|div|li|tr|h[1-4]|blockquote)>", "\n", texte)
    texte = re.sub(r"(?i)<li[^>]*>", "· ", texte)
    # Un lien devient « libellé (adresse) », sauf si le libellé est déjà l'adresse.
    def _lien(correspondance):
        url, libelle = correspondance["url"], re.sub(r"<[^>]+>", "", correspondance["libelle"]).strip()
        return libelle if libelle in ("", url) else f"{libelle} ({url})"

    texte = re.sub(r'(?is)<a[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<libelle>.*?)</a>', _lien, texte)
    texte = unescape(re.sub(r"<[^>]+>", "", texte))
    texte = re.sub(r"[ \t ]+", " ", texte)
    return re.sub(r"\n{3,}", "\n\n", texte).strip()
