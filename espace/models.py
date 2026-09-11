import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.validators import MaxValueValidator
from django.db import models


class StockagePrive(FileSystemStorage):
    """Documents clients : hors de tout dossier servi publiquement, lus seulement via une vue
    qui vérifie le propriétaire. L'emplacement suit le réglage ESPACE_DOCUMENTS_ROOT (y compris
    quand un test le modifie)."""

    @property
    def base_location(self):
        return settings.ESPACE_DOCUMENTS_ROOT

    @property
    def location(self):
        return str(settings.ESPACE_DOCUMENTS_ROOT)

    @property
    def base_url(self):
        return None


stockage_prive = StockagePrive()


def chemin_document(document, nom_fichier):
    # Un dossier aléatoire par fichier : le chemin ne se devine pas et deux clients peuvent
    # déposer un fichier du même nom sans collision.
    return f"{document.client_id}/{uuid.uuid4().hex}/{nom_fichier}"


class Projet(models.Model):
    """Ce que Satkaar mène pour un client : mission de conseil, formation ou déploiement."""

    class Type(models.TextChoices):
        CONSEIL = "conseil", "Mission de conseil"
        FORMATION = "formation", "Formation"
        LOGICIEL = "logiciel", "Déploiement de logiciel"

    class Statut(models.TextChoices):
        A_VENIR = "a_venir", "À venir"
        EN_COURS = "en_cours", "En cours"
        TERMINE = "termine", "Terminé"

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projets", verbose_name="client"
    )
    titre = models.CharField("titre", max_length=160)
    type = models.CharField("type", max_length=20, choices=Type.choices)
    statut = models.CharField("statut", max_length=20, choices=Statut.choices, default=Statut.EN_COURS)
    avancement = models.PositiveSmallIntegerField(
        "avancement", default=0, validators=[MaxValueValidator(100)], help_text="En pourcentage, de 0 à 100."
    )
    prochaine_etape = models.CharField("prochaine étape", max_length=200, blank=True)
    debut = models.DateField("début", null=True, blank=True)
    fin = models.DateField("fin prévue", null=True, blank=True)
    mis_a_jour = models.DateTimeField("mis à jour le", auto_now=True)

    class Meta:
        verbose_name = "projet"
        verbose_name_plural = "projets"
        ordering = ["-mis_a_jour"]

    def __str__(self):
        return f"{self.titre} — {self.client.email or self.client.username}"


class Document(models.Model):
    """Un fichier mis à disposition d'un client : facture, livrable, attestation…"""

    class Categorie(models.TextChoices):
        FACTURE = "facture", "Facture"
        LIVRABLE = "livrable", "Livrable"
        ATTESTATION = "attestation", "Attestation"
        AUTRE = "autre", "Autre document"

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents", verbose_name="client"
    )
    projet = models.ForeignKey(
        Projet, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents", verbose_name="projet"
    )
    titre = models.CharField("titre", max_length=160)
    categorie = models.CharField("catégorie", max_length=20, choices=Categorie.choices, default=Categorie.AUTRE)
    fichier = models.FileField("fichier", upload_to=chemin_document, storage=stockage_prive)
    ajoute_le = models.DateTimeField("ajouté le", auto_now_add=True)

    class Meta:
        verbose_name = "document"
        verbose_name_plural = "documents"
        ordering = ["-ajoute_le"]

    def __str__(self):
        return self.titre

    def clean(self):
        if self.projet_id and self.client_id and self.projet.client_id != self.client_id:
            raise ValidationError({"projet": "Ce projet appartient à un autre client."})

    @property
    def nom_fichier(self):
        return self.fichier.name.rsplit("/", 1)[-1]
