from django.conf import settings
from django.db import models


class Evenement(models.Model):
    """Rendez-vous, formation, déploiement… de l'agenda partagé de l'équipe."""

    class Categorie(models.TextChoices):
        RENDEZ_VOUS = "rendez_vous", "Rendez-vous client"
        FORMATION = "formation", "Formation"
        DEPLOIEMENT = "deploiement", "Déploiement"
        INTERNE = "interne", "Interne"
        AUTRE = "autre", "Autre"

    titre = models.CharField(max_length=200)
    categorie = models.CharField("catégorie", max_length=20, choices=Categorie.choices, default=Categorie.RENDEZ_VOUS)
    debut = models.DateTimeField("début", db_index=True)
    fin = models.DateTimeField()
    journee_entiere = models.BooleanField("journée entière", default=False)
    organisation = models.CharField("client ou organisation", max_length=160, blank=True)
    lieu = models.CharField(max_length=200, blank=True)
    lien_visio = models.URLField("lien visio", blank=True)
    description = models.TextField(blank=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="evenements_agenda")
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("debut",)
        verbose_name = "événement d'agenda"
        verbose_name_plural = "événements d'agenda"

    def __str__(self):
        return self.titre
