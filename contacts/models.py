from decimal import Decimal

from django.conf import settings
from django.db import models

# Tarif public d'Isidor (page produit) : 29,90 € HT par mois et par exploitation + 0,33 € HT par hectare et par mois.
ISIDOR_MENSUEL = Decimal("29.90")
ISIDOR_HECTARE = Decimal("0.33")


class Contact(models.Model):
    """Prospect ou client, suivi dans le pipeline commercial d'un produit."""

    class Produit(models.TextChoices):
        ISIDOR = "isidor", "Isidor"
        VANESSA = "vanessa", "Vanessa"
        BERNARD = "bernard", "Bernard"
        KATARINA = "katarina", "Katarina"
        CONSEIL = "conseil", "Conseil"
        FORMATION = "formation", "Formation"
        AUTRE = "autre", "À qualifier"

    class Statut(models.TextChoices):
        LEAD = "lead", "Lead"
        CONTACTE = "contacte", "Contacté"
        DEMO = "demo", "Démo"
        PROPOSITION = "proposition", "Proposition"
        CLIENT = "client", "Client"
        PERDU = "perdu", "Perdu"

    class Source(models.TextChoices):
        SITE = "site", "Formulaire du site"
        APPEL = "appel", "Appel entrant"
        RECOMMANDATION = "recommandation", "Recommandation"
        SALON = "salon", "Salon, événement"
        LINKEDIN = "linkedin", "LinkedIn"
        PROSPECTION = "prospection", "Prospection"
        AUTRE = "autre", "Autre"

    EN_COURS = (Statut.LEAD, Statut.CONTACTE, Statut.DEMO, Statut.PROPOSITION)
    # Ce que mesure le champ « taille », selon le produit.
    TAILLES = {"isidor": "Surface (ha)", "vanessa": "Habitants", "bernard": "Biens gérés", "katarina": "Conseillers",
               "conseil": "Jours estimés", "formation": "Participants", "autre": "Taille"}

    nom = models.CharField("nom", max_length=160)
    organisation = models.CharField("organisation", max_length=160, blank=True)
    fonction = models.CharField("fonction", max_length=120, blank=True)
    courriel = models.EmailField("courriel", blank=True)
    telephone = models.CharField("téléphone", max_length=40, blank=True)
    ville = models.CharField("commune", max_length=120, blank=True)
    produit = models.CharField("produit", max_length=20, choices=Produit.choices, default=Produit.AUTRE)
    statut = models.CharField("étape", max_length=20, choices=Statut.choices, default=Statut.LEAD)
    source = models.CharField("source", max_length=20, choices=Source.choices, default=Source.AUTRE)
    taille = models.PositiveIntegerField("taille", null=True, blank=True,
                                         help_text="Hectares pour Isidor, habitants pour Vanessa, biens gérés pour Bernard…")
    montant = models.DecimalField("montant estimé (€ HT par an)", max_digits=10, decimal_places=2, null=True, blank=True,
                                  help_text="Vide pour Isidor : calculé d'après la surface et le tarif public.")
    prochaine_relance = models.DateField("prochaine relance", null=True, blank=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="contacts_suivis")
    demande = models.ForeignKey("pages.DemandeDemonstration", on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="contacts", verbose_name="demande d'origine")
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-modifie_le",)
        verbose_name = "contact"
        indexes = [models.Index(fields=["produit", "statut"], name="contact_pipeline_idx")]

    def __str__(self):
        return f"{self.nom} — {self.organisation}" if self.organisation else self.nom

    @property
    def en_cours(self):
        return self.statut in self.EN_COURS

    @property
    def estime(self):
        """Montant saisi, sinon estimation Isidor d'après la surface."""
        return self.montant is None and self.produit == self.Produit.ISIDOR and self.taille is not None

    @property
    def potentiel(self):
        if self.montant is not None:
            return self.montant
        if self.estime:
            return ((ISIDOR_MENSUEL + ISIDOR_HECTARE * self.taille) * 12).quantize(Decimal("1"))
        return None

    @property
    def libelle_taille(self):
        return self.TAILLES.get(self.produit, "Taille")

    @property
    def initiales(self):
        mots = [m for m in self.nom.split() if m]
        return "".join(m[0] for m in mots[:2]).upper() or "?"


class Note(models.Model):
    """Échange avec un contact : appel, rendez-vous, mail ou simple note."""

    class Type(models.TextChoices):
        NOTE = "note", "Note"
        APPEL = "appel", "Appel"
        RENDEZ_VOUS = "rendez_vous", "Rendez-vous"
        MAIL = "mail", "Mail"
        ETAPE = "etape", "Changement d'étape"

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="notes")
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.NOTE)
    texte = models.TextField()
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-cree_le",)
        verbose_name = "échange"

    def __str__(self):
        return self.texte[:60]
