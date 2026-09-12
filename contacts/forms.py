from django import forms
from django.contrib.auth import get_user_model

from pages.forms import ChampsAccessiblesMixin

from .models import Contact, Note


class ChampEquipe(forms.ModelChoiceField):
    def label_from_instance(self, utilisateur):
        return utilisateur.get_full_name() or utilisateur.email


class ContactForm(ChampsAccessiblesMixin, forms.ModelForm):
    responsable = ChampEquipe(queryset=get_user_model().objects.none(), required=False, label="Suivi par",
                              empty_label="Personne pour l'instant")

    class Meta:
        model = Contact
        fields = ["nom", "organisation", "fonction", "courriel", "telephone", "ville", "produit", "statut", "source",
                  "taille", "montant", "prochaine_relance", "responsable"]
        widgets = {"prochaine_relance": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["responsable"].queryset = get_user_model().objects.filter(is_staff=True, is_active=True).order_by("first_name")
        self._preparer_champs()


class NoteForm(ChampsAccessiblesMixin, forms.ModelForm):
    class Meta:
        model = Note
        fields = ["type", "texte"]
        widgets = {"type": forms.RadioSelect,
                   "texte": forms.Textarea(attrs={"rows": 3, "placeholder": "Compte rendu d'appel, prochaine étape, objection…"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type"].choices = [c for c in Note.Type.choices if c[0] != Note.Type.ETAPE]
        self.fields["type"].initial = Note.Type.NOTE
        self._preparer_champs()
        self.fields["type"].widget.attrs.pop("class", None)
