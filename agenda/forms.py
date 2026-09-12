import secrets
from datetime import datetime, time, timedelta

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify

from pages.forms import ChampsAccessiblesMixin

from .models import Evenement


class ChampEquipe(forms.ModelMultipleChoiceField):
    def label_from_instance(self, utilisateur):
        return utilisateur.get_full_name() or utilisateur.email


class EvenementForm(ChampsAccessiblesMixin, forms.ModelForm):
    date_debut = forms.DateField(label="Date", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    heure_debut = forms.TimeField(label="De", required=False, widget=forms.TimeInput(attrs={"type": "time", "step": 300}, format="%H:%M"))
    date_fin = forms.DateField(label="Jusqu'au", required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
                               help_text="Pour un événement sur plusieurs jours.")
    heure_fin = forms.TimeField(label="À", required=False, widget=forms.TimeInput(attrs={"type": "time", "step": 300}, format="%H:%M"))
    generer_visio = forms.BooleanField(label="Créer un lien de visio (Jitsi)", required=False)
    participants = ChampEquipe(queryset=get_user_model().objects.none(), required=False,
                               widget=forms.CheckboxSelectMultiple, label="Participants de l'équipe")

    class Meta:
        model = Evenement
        fields = ["titre", "categorie", "journee_entiere", "organisation", "lieu", "lien_visio", "description", "participants"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["participants"].queryset = get_user_model().objects.filter(is_staff=True, is_active=True).order_by("first_name", "email")
        if self.instance.pk:
            debut, fin = timezone.localtime(self.instance.debut), timezone.localtime(self.instance.fin)
            if self.instance.journee_entiere:
                fin -= timedelta(days=1)  # la fin enregistrée est exclusive (minuit du lendemain)
            self.initial.update({"date_debut": debut.date(), "heure_debut": debut.time(),
                                 "date_fin": fin.date() if fin.date() != debut.date() else None, "heure_fin": fin.time()})
        self._preparer_champs()
        for nom in ("journee_entiere", "generer_visio", "participants"):
            self.fields[nom].widget.attrs["class"] = "case"

    def clean(self):
        donnees = super().clean()
        jour = donnees.get("date_debut")
        if not jour:
            return donnees
        jour_fin = donnees.get("date_fin") or jour
        if jour_fin < jour:
            self.add_error("date_fin", "La date de fin précède la date de début.")
            return donnees
        if donnees.get("journee_entiere"):
            debut = datetime.combine(jour, time(0))
            fin = datetime.combine(jour_fin + timedelta(days=1), time(0))
        else:
            if not donnees.get("heure_debut"):
                self.add_error("heure_debut", "Indiquez l'heure de début, ou cochez « Journée entière ».")
                return donnees
            debut = datetime.combine(jour, donnees["heure_debut"])
            fin = datetime.combine(jour_fin, donnees.get("heure_fin") or (debut + timedelta(hours=1)).time())
            if fin <= debut:
                self.add_error("heure_fin", "L'heure de fin doit suivre l'heure de début.")
                return donnees
        donnees["debut"], donnees["fin"] = timezone.make_aware(debut), timezone.make_aware(fin)
        return donnees

    def save(self, commit=True):
        evenement = super().save(commit=False)
        evenement.debut, evenement.fin = self.cleaned_data["debut"], self.cleaned_data["fin"]
        if self.cleaned_data.get("generer_visio") and not evenement.lien_visio:
            nom = slugify(evenement.titre)[:40] or "reunion"
            evenement.lien_visio = f"https://meet.jit.si/Satkaar-{nom}-{secrets.token_hex(4)}"
        if commit:
            evenement.save()
            self.save_m2m()
        return evenement
