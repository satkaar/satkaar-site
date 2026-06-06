from django.db import models


class MessageContact(models.Model):
    """Demande de contact envoyée via le formulaire en bas de page."""

    nom = models.CharField("Nom", max_length=200)
    fonction = models.CharField("Fonction", max_length=200)
    commune = models.CharField("Commune ou intercommunalité", max_length=200)
    email = models.EmailField("Email")
    telephone = models.CharField("Téléphone", max_length=30, blank=True)
    message = models.TextField("Message")
    consentement_rgpd = models.BooleanField("Consentement RGPD", default=False)
    cree_le = models.DateTimeField(auto_now_add=True)
    traite = models.BooleanField("Traité", default=False)

    class Meta:
        ordering = ["-cree_le"]
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"

    def __str__(self):
        return f"{self.nom} ({self.commune}) – {self.cree_le:%Y-%m-%d}"
