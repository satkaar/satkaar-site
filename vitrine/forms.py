from django import forms
from django.core.exceptions import ValidationError

from .models import MessageContact


class ContactForm(forms.ModelForm):
    """Formulaire de contact avec honeypot anti-spam."""

    # Champ piège : doit rester vide. Les bots remplissent tout.
    site_web = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}),
        label="Site web",
    )

    consentement_rgpd = forms.BooleanField(
        required=True,
        label=(
            "J'accepte que mes données soient utilisées par Satkaar SAS pour "
            "me recontacter dans le cadre de ma demande."
        ),
        error_messages={"required": "Le consentement RGPD est obligatoire."},
    )

    class Meta:
        model = MessageContact
        fields = ["nom", "fonction", "commune", "email", "telephone", "message", "consentement_rgpd"]
        widgets = {
            "nom": forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Jean Dupont"}),
            "fonction": forms.TextInput(attrs={"placeholder": "Maire, DGS, chef de service…"}),
            "commune": forms.TextInput(attrs={"placeholder": "Ex. Forcalquier"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "jean.dupont@mairie.fr"}),
            "telephone": forms.TextInput(attrs={"autocomplete": "tel", "placeholder": "06 12 34 56 78"}),
            "message": forms.Textarea(attrs={"rows": 5, "placeholder": "Quelques mots sur votre commune et vos enjeux numériques…"}),
        }

    def clean_site_web(self):
        value = self.cleaned_data.get("site_web", "")
        if value:
            # Honeypot rempli : on traite comme spam mais on ne le dit pas.
            raise ValidationError("Erreur de validation.")
        return value
