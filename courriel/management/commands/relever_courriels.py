"""Relève les boîtes mail de l'équipe. Une fois : `python manage.py relever_courriels` (tâche cron),
ou en continu : `python manage.py relever_courriels --boucle 120`."""

import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from courriel.models import CompteCourriel
from courriel.protocoles import ErreurCourriel, relever


class Command(BaseCommand):
    help = "Importe les nouveaux messages des boîtes mail actives."

    def add_arguments(self, parser):
        parser.add_argument("--boucle", type=int, default=0, help="Relever toutes les N secondes (60 minimum).")
        parser.add_argument("--limite", type=int, default=50, help="Messages récents examinés par boîte.")

    def handle(self, *args, boucle, limite, **options):
        while True:
            close_old_connections()
            for compte in CompteCourriel.objects.filter(actif=True):
                try:
                    nouveaux = relever(compte, limite=limite)
                    self.stdout.write(f"{compte.adresse} : {nouveaux} nouveau(x)")
                except ErreurCourriel as erreur:
                    CompteCourriel.objects.filter(pk=compte.pk).update(derniere_erreur=str(erreur)[:300])
                    self.stderr.write(f"{compte.adresse} : {erreur}")
            if not boucle:
                break
            time.sleep(max(60, boucle))
