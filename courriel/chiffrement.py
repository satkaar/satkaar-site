"""Chiffrement des mots de passe des boîtes mail (Fernet, AES + HMAC).

La clé vient du réglage COURRIEL_CLE (variable d'environnement, clé Fernet). À défaut, elle est
dérivée de SECRET_KEY : changer SECRET_KEY oblige alors à ressaisir les mots de passe des boîtes.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet():
    cle = getattr(settings, "COURRIEL_CLE", "")
    if not cle:
        empreinte = hashlib.sha256(f"satkaar-courriel:{settings.SECRET_KEY}".encode()).digest()
        cle = base64.urlsafe_b64encode(empreinte)
    return Fernet(cle)


def chiffrer(texte):
    return _fernet().encrypt(texte.encode()) if texte else b""


def dechiffrer(octets):
    if not octets:
        return ""
    try:
        return _fernet().decrypt(bytes(octets)).decode()
    except InvalidToken:
        # Clé changée depuis l'enregistrement : le mot de passe est à ressaisir.
        return ""
