import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from mesure.models import Evenement, Mesure, PageVue, PassageRobot


class Command(BaseCommand):
    help = "Supprime les données de mesure d'audience plus anciennes que la durée de conservation (13 mois)."

    def add_arguments(self, parser):
        parser.add_argument("--mois", type=int, default=13)

    def handle(self, *args, mois, **options):
        limite = timezone.now() - datetime.timedelta(days=round(mois * 30.44))
        for modele in (PageVue, Mesure, Evenement, PassageRobot):
            supprimes, _ = modele.objects.filter(horodatage__lt=limite).delete()
            self.stdout.write(f"{modele._meta.verbose_name_plural} : {supprimes} supprimé(s)")
