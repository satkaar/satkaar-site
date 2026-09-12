"""Mesure d'audience maison, sans cookie ni service tiers.

Aucune adresse IP n'est stockée : un visiteur est représenté par une empreinte calculée à
partir de l'IP et du navigateur avec un sel qui change chaque jour. Elle ne permet ni de
retrouver la personne ni de la suivre d'un jour à l'autre. Conservation : 13 mois au plus
(commande purger_mesures).
"""

from django.db import models
from django.utils import timezone


class PageVue(models.Model):
    class Source(models.TextChoices):
        DIRECT = "direct", "Accès direct"
        MOTEUR = "moteur", "Moteurs de recherche"
        IA = "ia", "Assistants IA"
        SOCIAL = "social", "Réseaux sociaux"
        SITE = "site", "Sites référents"
        CAMPAGNE = "campagne", "Campagnes"
        INTERNE = "interne", "Navigation interne"

    horodatage = models.DateTimeField(default=timezone.now, db_index=True)
    chemin = models.CharField(max_length=300, db_index=True)
    statut = models.PositiveSmallIntegerField(default=200)
    visiteur = models.CharField(max_length=16, db_index=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.DIRECT)
    referent = models.CharField(max_length=120, blank=True)
    utm_source = models.CharField(max_length=80, blank=True)
    utm_medium = models.CharField(max_length=80, blank=True)
    utm_campagne = models.CharField(max_length=80, blank=True)
    appareil = models.CharField(max_length=12, blank=True)
    navigateur = models.CharField(max_length=30, blank=True)
    systeme = models.CharField(max_length=30, blank=True)
    langue = models.CharField(max_length=10, blank=True)
    duree_serveur_ms = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "page vue"
        verbose_name_plural = "pages vues"
        ordering = ["-horodatage"]


class Mesure(models.Model):
    """Engagement et performance d'une page vue, envoyés par le navigateur à la sortie."""

    horodatage = models.DateTimeField(default=timezone.now, db_index=True)
    chemin = models.CharField(max_length=300, db_index=True)
    visiteur = models.CharField(max_length=16, db_index=True)
    temps_actif_s = models.PositiveIntegerField(default=0)
    defilement = models.PositiveSmallIntegerField(default=0)
    lcp_ms = models.PositiveIntegerField(null=True, blank=True)
    cls = models.FloatField(null=True, blank=True)
    inp_ms = models.PositiveIntegerField(null=True, blank=True)
    fcp_ms = models.PositiveIntegerField(null=True, blank=True)
    ttfb_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "mesure de page"
        verbose_name_plural = "mesures de page"


class Evenement(models.Model):
    class Type(models.TextChoices):
        TELEPHONE = "telephone", "Clic sur le téléphone"
        COURRIEL = "courriel", "Clic sur le courriel"
        APPEL_ACTION = "appel_action", "Clic sur un appel à l'action"
        SORTANT = "sortant", "Lien sortant"
        FAQ = "faq", "Question de FAQ ouverte"
        DICTEE = "dictee", "Dictée vocale lancée"
        REFORMULATION = "reformulation", "Reformulation par l'IA"
        CONNEXION = "connexion", "Connexion à l'espace client"
        TELECHARGEMENT = "telechargement", "Document téléchargé"

    horodatage = models.DateTimeField(default=timezone.now, db_index=True)
    visiteur = models.CharField(max_length=16, blank=True)
    chemin = models.CharField(max_length=300, blank=True)
    type = models.CharField(max_length=20, choices=Type.choices, db_index=True)
    cible = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "événement"
        verbose_name_plural = "événements"


class PassageRobot(models.Model):
    class Famille(models.TextChoices):
        IA = "ia", "Robots d'IA"
        MOTEUR = "moteur", "Moteurs de recherche"
        AUTRE = "autre", "Autres robots"

    horodatage = models.DateTimeField(default=timezone.now, db_index=True)
    robot = models.CharField(max_length=40)
    famille = models.CharField(max_length=10, choices=Famille.choices)
    chemin = models.CharField(max_length=300)

    class Meta:
        verbose_name = "passage de robot"
        verbose_name_plural = "passages de robots"
