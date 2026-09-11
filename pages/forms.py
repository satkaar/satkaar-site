import calendar
import datetime

from django import forms
from django.utils import formats, timezone

from .models import DemandeDemonstration

JOURS_COURTS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
MOIS_COURTS = ["Janv", "Févr", "Mars", "Avr", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]

# Rappel : les jours ouvrés des deux prochains mois, par demi-heure.
MOIS_DE_RAPPEL = 2
HEURES_DE_RAPPEL = {
    "Matin": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30"],
    "Après-midi": ["14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"],
}


def ajouter_mois(jour, mois):
    """Même quantième, `mois` plus tard ; ramené au dernier jour du mois si besoin (31 → 30)."""
    annee, rang = divmod(jour.month - 1 + mois, 12)
    annee += jour.year
    dernier = calendar.monthrange(annee, rang + 1)[1]
    return jour.replace(year=annee, month=rang + 1, day=min(jour.day, dernier))


def jours_ouvres_a_venir(aujourdhui, mois=MOIS_DE_RAPPEL):
    """Du lundi au vendredi, de demain jusqu'à la même date dans `mois` mois."""
    fin = ajouter_mois(aujourdhui, mois)
    jours, jour = [], aujourdhui + datetime.timedelta(days=1)
    while jour <= fin:
        if jour.weekday() < 5:
            jours.append(jour)
        jour += datetime.timedelta(days=1)
    return jours


class ChampsAccessiblesMixin:
    """Classe CSS commune et signalement des champs fautifs aux technologies d'assistance."""

    def _preparer_champs(self):
        for nom_champ, champ in self.fields.items():
            champ.widget.attrs.setdefault("class", "champ")
            if champ.required:
                champ.widget.attrs["aria-required"] = "true"

        if self.is_bound:
            # self.errors déclenche la validation : on peut alors signaler les
            # champs fautifs aux technologies d'assistance (RGAA 11.10).
            for nom_champ in self.errors:
                if nom_champ in self.fields:
                    widget = self.fields[nom_champ].widget
                    widget.attrs["aria-invalid"] = "true"
                    widget.attrs["aria-describedby"] = f"{self[nom_champ].auto_id}-erreur"


class DemandeDemonstrationForm(ChampsAccessiblesMixin, forms.ModelForm):
    """Formulaire court : qui vous êtes, votre sujet, et un moment pour être rappelé."""

    rappel_jour = forms.TypedChoiceField(
        label="Quel jour ?",
        required=False,
        initial="",
        coerce=datetime.date.fromisoformat,
        empty_value=None,
        widget=forms.RadioSelect,
    )
    rappel_heure = forms.TypedChoiceField(
        label="À quelle heure ?",
        required=False,
        initial="",
        coerce=datetime.time.fromisoformat,
        empty_value=None,
        choices=[("", "Peu importe")]
        + [(heure, heure) for heures in HEURES_DE_RAPPEL.values() for heure in heures],
        widget=forms.RadioSelect,
    )

    class Meta:
        model = DemandeDemonstration
        fields = [
            "nom", "organisation", "fonction", "courriel", "sujet", "telephone",
            "rappel_jour", "rappel_heure", "message",
        ]
        labels = {
            "nom": "Nom et prénom",
            "organisation": "Organisation",
            "sujet": "Votre demande concerne",
            "fonction": "Fonction",
            "courriel": "Courriel",
            "telephone": "Téléphone",
            "message": "Votre message",
        }
        widgets = {
            "nom": forms.TextInput(attrs={"autocomplete": "name"}),
            "organisation": forms.TextInput(
                attrs={"autocomplete": "organization", "placeholder": "Entreprise, exploitation, commune, agence…"}
            ),
            "fonction": forms.TextInput(
                attrs={"autocomplete": "organization-title", "placeholder": "Dirigeant, DSI, maire, exploitant…"}
            ),
            "courriel": forms.EmailInput(attrs={"autocomplete": "email"}),
            "telephone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
            "message": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Votre projet ou ce que vous cherchez à régler, en deux lignes."}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fonction"].required = False
        self.fields["telephone"].required = False
        self.fields["message"].required = False
        self.fields["sujet"].choices = [("", "Choisir…")] + list(DemandeDemonstration.Sujet.choices)
        # Sans sujet transmis par la page d'origine, le visiteur choisit lui-même.
        self.fields["sujet"].initial = None
        self._jours = jours_ouvres_a_venir(timezone.localdate())
        self.fields["rappel_jour"].choices = [("", "Peu importe")] + [
            (jour.isoformat(), jour.isoformat()) for jour in self._jours
        ]
        self._preparer_champs()
        # Les pastilles de rappel ne portent pas la classe des champs texte.
        for nom_champ in ("rappel_jour", "rappel_heure"):
            self.fields[nom_champ].widget.attrs.pop("class", None)

    def clean(self):
        donnees = super().clean()
        souhaite_rappel = donnees.get("rappel_jour") or donnees.get("rappel_heure")
        if souhaite_rappel and not donnees.get("telephone"):
            self.add_error("telephone", "Indiquez un numéro pour que nous puissions vous rappeler.")
        return donnees

    # --- Données d'affichage des pastilles de rappel -------------------------

    def jours_de_rappel(self):
        coche = str(self["rappel_jour"].value() or "")
        demain = timezone.localdate() + datetime.timedelta(days=1)
        pastilles = [{"valeur": "", "coche": coche == ""}]
        for jour in self._jours:
            pastilles.append({
                "valeur": jour.isoformat(),
                "coche": coche == jour.isoformat(),
                "en_tete": "Demain" if jour == demain else JOURS_COURTS[jour.weekday()],
                "numero": jour.day,
                "mois": MOIS_COURTS[jour.month - 1],
                "complet": formats.date_format(jour, "l j F"),
            })
        return pastilles

    def heures_de_rappel(self):
        coche = str(self["rappel_heure"].value() or "")[:5]
        return [
            {"moment": moment, "heures": [{"valeur": h, "coche": coche == h} for h in heures]}
            for moment, heures in HEURES_DE_RAPPEL.items()
        ]

    def heure_indifferente(self):
        return not self["rappel_heure"].value()

