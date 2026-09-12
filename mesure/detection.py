"""Reconnaissance des robots, des appareils et des sources de trafic, sans bibliothèque tierce."""

import datetime
import hashlib
import re
from urllib.parse import urlparse

from django.conf import settings

# (motif dans le User-Agent, nom affiché, famille). L'ordre compte : le premier qui correspond gagne.
ROBOTS = [
    ("GPTBot", "GPTBot (OpenAI)", "ia"),
    ("OAI-SearchBot", "OAI-SearchBot (ChatGPT)", "ia"),
    ("ChatGPT-User", "ChatGPT-User", "ia"),
    ("ClaudeBot", "ClaudeBot (Anthropic)", "ia"),
    ("Claude-SearchBot", "Claude-SearchBot", "ia"),
    ("Claude-User", "Claude-User", "ia"),
    ("anthropic-ai", "Anthropic", "ia"),
    ("PerplexityBot", "PerplexityBot", "ia"),
    ("Perplexity-User", "Perplexity-User", "ia"),
    ("MistralAI-User", "Mistral AI", "ia"),
    ("Google-Extended", "Google-Extended (Gemini)", "ia"),
    ("GoogleOther", "GoogleOther", "ia"),
    ("Applebot-Extended", "Applebot-Extended", "ia"),
    ("meta-externalagent", "Meta AI", "ia"),
    ("Bytespider", "Bytespider (ByteDance)", "ia"),
    ("CCBot", "CCBot (Common Crawl)", "ia"),
    ("Amazonbot", "Amazonbot", "ia"),
    ("cohere-ai", "Cohere", "ia"),
    ("DuckAssistBot", "DuckAssistBot", "ia"),
    ("Googlebot", "Googlebot", "moteur"),
    ("bingbot", "Bingbot", "moteur"),
    ("Applebot", "Applebot", "moteur"),
    ("DuckDuckBot", "DuckDuckBot", "moteur"),
    ("Qwantbot", "Qwantbot", "moteur"),
    ("YandexBot", "YandexBot", "moteur"),
    ("Baiduspider", "Baiduspider", "moteur"),
    ("Ecosia", "Ecosia", "moteur"),
]
ROBOT_GENERIQUE = re.compile(
    r"bot|crawl|spider|slurp|curl|wget|python-requests|httpx|headlesschrome|lighthouse|"
    r"facebookexternalhit|linkedinbot|embedly|preview|monitor|uptime",
    re.I,
)

MOTEURS = ["google.", "bing.com", "duckduckgo.com", "qwant.com", "ecosia.org", "yahoo.",
           "search.brave.com", "startpage.com", "yandex.", "baidu.com", "lilo.org"]
ASSISTANTS_IA = ["chatgpt.com", "chat.openai.com", "perplexity.ai", "claude.ai", "gemini.google.com",
                 "copilot.microsoft.com", "chat.mistral.ai", "you.com", "deepseek.com", "meta.ai",
                 "phind.com", "poe.com"]
RESEAUX_SOCIAUX = ["linkedin.com", "lnkd.in", "facebook.com", "fb.me", "instagram.com", "t.co",
                   "x.com", "twitter.com", "youtube.com", "whatsapp.com", "reddit.com", "bsky.app",
                   "threads.net", "pinterest.", "tiktok.com"]


def robot(user_agent):
    """(nom, famille) si le visiteur est un robot, sinon None."""
    for motif, nom, famille in ROBOTS:
        if motif.lower() in user_agent.lower():
            return nom, famille
    if not user_agent or ROBOT_GENERIQUE.search(user_agent):
        nom = (user_agent.split("/")[0] or "Inconnu")[:40]
        return nom, "autre"
    return None


def appareil(ua):
    if re.search(r"iPad|Tablet|PlayBook|Silk", ua) or ("Android" in ua and "Mobile" not in ua):
        return "Tablette"
    if re.search(r"Mobi|iPhone|iPod|Android", ua):
        return "Mobile"
    return "Ordinateur"


def navigateur(ua):
    for motif, nom in [("Edg/", "Edge"), ("OPR/", "Opera"), ("SamsungBrowser", "Samsung Internet"),
                       ("Firefox/", "Firefox"), ("FxiOS", "Firefox"), ("CriOS", "Chrome"),
                       ("Chrome/", "Chrome"), ("Safari/", "Safari")]:
        if motif in ua:
            return nom
    return "Autre"


def systeme(ua):
    for motif, nom in [("iPhone", "iOS"), ("iPad", "iPadOS"), ("Android", "Android"), ("CrOS", "ChromeOS"),
                       ("Windows", "Windows"), ("Macintosh", "macOS"), ("Linux", "Linux")]:
        if motif in ua:
            return nom
    return "Autre"


def langue(accept_language):
    premiere = (accept_language or "").split(",")[0].split(";")[0].strip().lower()
    return premiere.split("-")[0][:10]


def _correspond(domaine, liste):
    """« google. » couvre google.fr, google.com… ; « linkedin.com » couvre aussi fr.linkedin.com."""
    for motif in liste:
        if motif.endswith("."):
            if ("." + domaine).find("." + motif) != -1:
                return True
        elif domaine == motif or domaine.endswith("." + motif):
            return True
    return False


def source(referent, hote, utm_source):
    """(source, domaine référent). Les campagnes (utm_source) priment sur le référent."""
    domaine = (urlparse(referent).hostname or "").lower().removeprefix("www.") if referent else ""
    hote = hote.split(":")[0].lower().removeprefix("www.")
    if utm_source:
        return "campagne", domaine
    if not domaine:
        return "direct", ""
    if domaine == hote:
        return "interne", ""
    if _correspond(domaine, ASSISTANTS_IA):
        return "ia", domaine
    if _correspond(domaine, MOTEURS):
        return "moteur", domaine
    if _correspond(domaine, RESEAUX_SOCIAUX):
        return "social", domaine
    return "site", domaine


def empreinte(request):
    """Identifiant du visiteur pour la journée : l'IP n'est jamais conservée."""
    jour = datetime.date.today().isoformat()
    ip = request.META.get("REMOTE_ADDR", "")
    ua = request.META.get("HTTP_USER_AGENT", "")
    return hashlib.sha256(f"{jour}|{settings.SECRET_KEY}|{ip}|{ua}".encode()).hexdigest()[:16]


def refuse_le_suivi(request):
    """Signaux « Ne pas me suivre » (DNT) et Global Privacy Control : on ne mesure rien."""
    return request.META.get("HTTP_DNT") == "1" or request.META.get("HTTP_SEC_GPC") == "1"
