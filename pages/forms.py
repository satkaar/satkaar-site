from django import forms

from .models import DemandeDemonstration


class DemandeDemonstrationForm(forms.ModelForm):
    """Formulaire court : six champs, pas un de plus."""

    class Meta:
        model = DemandeDemonstration
        fields = ["nom", "collectivite", "fonction", "courriel", "telephone", "message"]
        labels = {
            "nom": "Nom et prénom",
            "collectivite": "Collectivité",
            "fonction": "Fonction",
            "courriel": "Courriel",
            "telephone": "Téléphone",
            "message": "Votre message",
        }
        widgets = {
            "nom": forms.TextInput(attrs={"autocomplete": "name"}),
            "collectivite": forms.TextInput(
                attrs={"autocomplete": "organization", "placeholder": "Commune, communauté de communes…"}
            ),
            "fonction": forms.TextInput(
                attrs={"autocomplete": "organization-title", "placeholder": "Maire, DGS, responsable de service…"}
            ),
            "courriel": forms.EmailInput(attrs={"autocomplete": "email"}),
            "telephone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
            "message": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Ce que vous cherchez à régler, en deux lignes."}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nom_champ, champ in self.fields.items():
            champ.widget.attrs.setdefault("class", "champ")
            if champ.required:
                champ.widget.attrs["aria-required"] = "true"
        self.fields["fonction"].required = False
        self.fields["telephone"].required = False
        self.fields["message"].required = False

        if self.is_bound:
            # self.errors déclenche la validation : on peut alors signaler les
            # champs fautifs aux technologies d'assistance (RGAA 11.10).
            for nom_champ in self.errors:
                if nom_champ in self.fields:
                    widget = self.fields[nom_champ].widget
                    widget.attrs["aria-invalid"] = "true"
                    widget.attrs["aria-describedby"] = f"{self.auto_id % nom_champ}-erreur"
