import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils.text import get_valid_filename

from espace.models import stockage_prive

from .chiffrement import chiffrer, dechiffrer


class CompteCourriel(models.Model):
    """Boîte mail de l'équipe (contact@satkaar.io…), relevée en IMAP et utilisée en SMTP."""

    class Securite(models.TextChoices):
        SSL = "ssl", "SSL/TLS (port 465)"
        STARTTLS = "starttls", "STARTTLS (port 587)"

    libelle = models.CharField("libellé", max_length=80, blank=True, help_text="Par exemple « Contact ». Vide : l'adresse est affichée.")
    adresse = models.EmailField("adresse", unique=True)
    nom_expediteur = models.CharField("nom affiché aux destinataires", max_length=80, default="Satkaar")
    identifiant = models.CharField("identifiant", max_length=255, help_text="Souvent l'adresse elle-même.")
    mot_de_passe_chiffre = models.BinaryField(editable=False, default=b"")
    imap_hote = models.CharField("serveur IMAP", max_length=120)
    imap_port = models.PositiveIntegerField("port IMAP", default=993)
    smtp_hote = models.CharField("serveur SMTP", max_length=120)
    smtp_port = models.PositiveIntegerField("port SMTP", default=465)
    smtp_securite = models.CharField("sécurité SMTP", max_length=10, choices=Securite.choices, default=Securite.SSL)
    actif = models.BooleanField("relever cette boîte", default=True)
    derniere_releve = models.DateTimeField("dernière relève", null=True, blank=True)
    derniere_erreur = models.CharField(max_length=300, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("libelle", "adresse")
        verbose_name = "boîte mail"
        verbose_name_plural = "boîtes mail"

    def __str__(self):
        return self.libelle or self.adresse

    @property
    def est_gmail(self):
        return self.imap_hote.lower().endswith(("gmail.com", "googlemail.com"))

    @property
    def copie_envoyes_automatique(self):
        """Gmail range lui-même dans « Envoyés » ce qui part par son SMTP : pas de seconde copie."""
        return self.est_gmail or self.smtp_hote.lower().endswith(("office365.com", "outlook.com"))

    @property
    def mot_de_passe(self):
        return dechiffrer(self.mot_de_passe_chiffre)

    @mot_de_passe.setter
    def mot_de_passe(self, clair):
        self.mot_de_passe_chiffre = chiffrer(clair)



class Signature(models.Model):
    """Bloc ajouté au bas des messages. Une boîte peut en avoir plusieurs (« Direction »,
    « Support »…) ; celle qui est cochée par défaut s'écrit toute seule à l'ouverture."""

    compte = models.ForeignKey(CompteCourriel, on_delete=models.CASCADE, related_name="signatures",
                               null=True, blank=True, verbose_name="boîte",
                               help_text="Vide : proposée pour toutes les boîtes.")
    libelle = models.CharField("nom", max_length=80, help_text="Pour la reconnaître : « Direction », « Support »…")
    corps = models.TextField("signature", help_text="Ajoutée sous « -- », au bas du message.")
    par_defaut = models.BooleanField("proposée par défaut", default=False)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-par_defaut", "libelle")
        verbose_name = "signature"

    def __str__(self):
        return self.libelle

    @property
    def texte(self):
        return f"-- \n{self.corps}"

    @property
    def html(self):
        from django.utils.html import escape
        return "<p>--<br>" + escape(self.corps).replace("\n", "<br>") + "</p>"

    @classmethod
    def disponibles(cls, compte=None):
        """Celles de la boîte, plus celles partagées par toutes les boîtes."""
        toutes = cls.objects.all()
        return toutes.filter(models.Q(compte=compte) | models.Q(compte__isnull=True)) if compte else toutes

    @classmethod
    def par_defaut_de(cls, compte):
        return cls.disponibles(compte).filter(par_defaut=True).first()


class Courriel(models.Model):
    class Dossier(models.TextChoices):
        RECEPTION = "reception", "Boîte de réception"
        ENVOYES = "envoyes", "Envoyés"

    compte = models.ForeignKey(CompteCourriel, on_delete=models.CASCADE, related_name="courriels")
    class Categorie(models.TextChoices):
        PRINCIPALE = "principale", "Principale"
        PROMOTIONS = "promotions", "Promotions"
        RESEAUX = "reseaux", "Réseaux sociaux"
        NOTIFICATIONS = "notifications", "Notifications"

    dossier = models.CharField(max_length=10, choices=Dossier.choices, default=Dossier.RECEPTION)
    categorie = models.CharField("catégorie", max_length=15, choices=Categorie.choices, default=Categorie.PRINCIPALE)
    message_id = models.CharField(max_length=512)
    uid = models.CharField("UID IMAP", max_length=40, blank=True)
    expediteur_nom = models.CharField(max_length=255, blank=True)
    expediteur_adresse = models.CharField(max_length=255, blank=True)
    destinataires = models.TextField(blank=True)
    copie = models.TextField(blank=True)
    repondre_a = models.CharField(max_length=255, blank=True)
    sujet = models.CharField(max_length=500, blank=True)
    texte = models.TextField(blank=True)
    html = models.TextField(blank=True)
    date = models.DateTimeField(db_index=True)
    en_reponse_a = models.CharField(max_length=512, blank=True)
    references = models.TextField(blank=True)
    lu = models.BooleanField(default=False)
    etoile = models.BooleanField("étoilé", default=False)
    corbeille = models.BooleanField(default=False)
    envoye_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ("-date",)
        verbose_name = "courriel"
        constraints = [
            models.UniqueConstraint(fields=["compte", "dossier", "message_id"], name="courriel_unique_par_dossier"),
        ]
        indexes = [models.Index(fields=["compte", "dossier", "corbeille", "-date"], name="courriel_liste_idx"),
                   models.Index(fields=["dossier", "categorie", "corbeille", "-date"], name="courriel_onglet_idx")]

    def __str__(self):
        return self.sujet or "(sans objet)"

    @property
    def envoye(self):
        return self.dossier == self.Dossier.ENVOYES

    @property
    def correspondant(self):
        """Ce qu'on affiche dans la liste : l'expéditeur, ou le destinataire pour un envoi."""
        if self.envoye:
            return f"À : {self.destinataires}" if self.destinataires else "(sans destinataire)"
        return self.expediteur_nom or self.expediteur_adresse or "(inconnu)"

    @property
    def initiale(self):
        nom = (self.destinataires if self.envoye else self.expediteur_nom or self.expediteur_adresse) or "?"
        return nom.strip()[:1].upper() or "?"

    @property
    def apercu(self):
        texte = " ".join(self.texte.split())
        return texte[:140] + ("…" if len(texte) > 140 else "")


def chemin_piece_jointe(piece, nom_fichier):
    nom = get_valid_filename(Path(nom_fichier).name) or "piece-jointe"
    return f"courriels/{uuid.uuid4().hex}/{nom[-120:]}"


class PieceJointe(models.Model):
    courriel = models.ForeignKey(Courriel, on_delete=models.CASCADE, related_name="pieces_jointes")
    nom = models.CharField(max_length=255)
    type_mime = models.CharField(max_length=120, default="application/octet-stream")
    taille = models.PositiveIntegerField(default=0)
    fichier = models.FileField(storage=stockage_prive, upload_to=chemin_piece_jointe)

    class Meta:
        verbose_name = "pièce jointe"
        verbose_name_plural = "pièces jointes"

    def __str__(self):
        return self.nom
