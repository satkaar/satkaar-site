from django.db import models


class DemandeDemonstration(models.Model):
    """Une demande de démonstration déposée depuis la page Contact."""

    nom = models.CharField("nom", max_length=120)
    collectivite = models.CharField("collectivité", max_length=160)
    fonction = models.CharField("fonction", max_length=120, blank=True)
    courriel = models.EmailField("courriel")
    telephone = models.CharField("téléphone", max_length=40, blank=True)
    message = models.TextField("message", blank=True)
    cree_le = models.DateTimeField("reçue le", auto_now_add=True)
    traitee = models.BooleanField("traitée", default=False)

    class Meta:
        verbose_name = "demande de démonstration"
        verbose_name_plural = "demandes de démonstration"
        ordering = ["-cree_le"]

    def __str__(self):
        return f"{self.nom} — {self.collectivite}"
