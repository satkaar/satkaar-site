from email.utils import getaddresses

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from pages.forms import ChampsAccessiblesMixin

from .models import CompteCourriel

PIECES_MAX = 20 * 1024 * 1024  # total des pièces jointes d'un envoi

# Réglages des hébergeurs courants ; satkaar.io est chez OVH (MX Plan).
FOURNISSEURS = {
    "ovh": {"libelle": "OVH (MX Plan)", "imap_hote": "ssl0.ovh.net", "imap_port": 993,
            "smtp_hote": "ssl0.ovh.net", "smtp_port": 465, "smtp_securite": "ssl"},
    "ovh_pro": {"libelle": "OVH Email Pro", "imap_hote": "pro1.mail.ovh.net", "imap_port": 993,
                "smtp_hote": "pro1.mail.ovh.net", "smtp_port": 587, "smtp_securite": "starttls"},
    "google": {"libelle": "Google Workspace / Gmail (mot de passe d'application)", "imap_hote": "imap.gmail.com",
               "imap_port": 993, "smtp_hote": "smtp.gmail.com", "smtp_port": 465, "smtp_securite": "ssl"},
    "infomaniak": {"libelle": "Infomaniak", "imap_hote": "mail.infomaniak.com", "imap_port": 993,
                   "smtp_hote": "mail.infomaniak.com", "smtp_port": 465, "smtp_securite": "ssl"},
    "ionos": {"libelle": "IONOS", "imap_hote": "imap.ionos.fr", "imap_port": 993,
              "smtp_hote": "smtp.ionos.fr", "smtp_port": 465, "smtp_securite": "ssl"},
}


def adresses(texte):
    """« Jean <jean@x.fr>; marie@y.fr » → ["jean@x.fr", "marie@y.fr"], chaque adresse vérifiée."""
    trouvees = [a for _, a in getaddresses([(texte or "").replace(";", ",")]) if a]
    for adresse in trouvees:
        try:
            validate_email(adresse)
        except ValidationError:
            raise ValidationError(f"Adresse invalide : {adresse}") from None
    return trouvees


class CompteForm(ChampsAccessiblesMixin, forms.ModelForm):
    mot_de_passe = forms.CharField(
        label="Mot de passe de la boîte", required=False, strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Chiffré avant d'être enregistré. En modification, laissez vide pour le conserver.",
    )

    class Meta:
        model = CompteCourriel
        fields = ["libelle", "adresse", "nom_expediteur", "identifiant", "mot_de_passe", "imap_hote", "imap_port",
                  "smtp_hote", "smtp_port", "smtp_securite", "signature", "actif"]
        widgets = {
            "identifiant": forms.TextInput(attrs={"autocomplete": "off"}),
            "signature": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["mot_de_passe"].required = True
            self.fields["mot_de_passe"].help_text = "Chiffré avant d'être enregistré."
        self._preparer_champs()
        self.fields["actif"].widget.attrs["class"] = "case"

    def save(self, commit=True):
        compte = super().save(commit=False)
        if self.cleaned_data.get("mot_de_passe"):
            compte.mot_de_passe = self.cleaned_data["mot_de_passe"]
        if commit:
            compte.save()
        return compte


class EnvoiMultiple(forms.ClearableFileInput):
    allow_multiple_selected = True


class ChampFichiers(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", EnvoiMultiple())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        nettoyer = super().clean
        if isinstance(data, (list, tuple)):
            return [nettoyer(d, initial) for d in data if d]
        return [nettoyer(data, initial)] if data else []


class ChampBoite(forms.ModelChoiceField):
    def label_from_instance(self, compte):
        return f"{compte.nom_expediteur} <{compte.adresse}>"


class RedactionForm(ChampsAccessiblesMixin, forms.Form):
    compte = ChampBoite(label="De", queryset=CompteCourriel.objects.filter(actif=True), empty_label=None)
    a = forms.CharField(label="À", widget=forms.TextInput(attrs={"autocomplete": "email", "placeholder": "nom@exemple.fr"}),
                        help_text="Plusieurs adresses : séparez-les par une virgule.")
    copie = forms.CharField(label="Cc", required=False)
    copie_cachee = forms.CharField(label="Cci", required=False)
    sujet = forms.CharField(label="Objet", max_length=500, required=False)
    texte = forms.CharField(label="Message", widget=forms.Textarea(attrs={"rows": 14}))
    pieces = ChampFichiers(label="Pièces jointes", required=False, help_text="20 Mo au total.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._preparer_champs()

    def clean_a(self):
        trouvees = adresses(self.cleaned_data["a"])
        if not trouvees:
            raise ValidationError("Indiquez au moins un destinataire.")
        return trouvees

    def clean_copie(self):
        return adresses(self.cleaned_data["copie"])

    def clean_copie_cachee(self):
        return adresses(self.cleaned_data["copie_cachee"])

    def clean_pieces(self):
        pieces = self.cleaned_data["pieces"]
        if sum(p.size for p in pieces) > PIECES_MAX:
            raise ValidationError("Les pièces jointes dépassent 20 Mo au total.")
        return pieces
