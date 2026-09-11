from django.db import models


class DemandeDemonstration(models.Model):
    """Une demande déposée depuis la page Contact : conseil ou démonstration d'un logiciel."""

    class Sujet(models.TextChoices):
        CONSEIL = "conseil", "Conseil (IA, data, systèmes d'information)"
        FORMATION = "formation", "Formation"
        ISIDOR = "isidor", "Isidor — agriculture"
        KATARINA = "katarina", "Katarina — chambres d'agriculture"
        VANESSA = "vanessa", "Vanessa — mairies"
        BERNARD = "bernard", "Bernard — immobilier"
        AUTRE = "autre", "Autre demande"

    nom = models.CharField("nom", max_length=120)
    organisation = models.CharField("organisation", max_length=160)
    sujet = models.CharField("sujet", max_length=20, choices=Sujet.choices, default=Sujet.AUTRE)
    fonction = models.CharField("fonction", max_length=120, blank=True)
    courriel = models.EmailField("courriel")
    telephone = models.CharField("téléphone", max_length=40, blank=True)
    message = models.TextField("message", blank=True)
    # Rappel souhaité ; vide = « peu importe ».
    rappel_jour = models.DateField("jour de rappel", null=True, blank=True)
    rappel_heure = models.TimeField("heure de rappel", null=True, blank=True)
    cree_le = models.DateTimeField("reçue le", auto_now_add=True)
    traitee = models.BooleanField("traitée", default=False)

    class Meta:
        verbose_name = "demande de contact"
        verbose_name_plural = "demandes de contact"
        ordering = ["-cree_le"]

    def __str__(self):
        return f"{self.nom} — {self.organisation}"

