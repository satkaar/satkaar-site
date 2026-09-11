from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.core.cache import cache

# Au-delà de ce nombre d'échecs pour un même courriel depuis une même adresse, on bloque un moment.
ESSAIS_MAX = 5
FENETRE_ESSAIS = 15 * 60  # secondes


def _habiller(form):
    for champ in form.fields.values():
        champ.widget.attrs.setdefault("class", "champ")


class ConnexionForm(AuthenticationForm):
    username = forms.EmailField(
        label="Courriel",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}),
    )
    error_messages = {
        "invalid_login": "Courriel ou mot de passe incorrect.",
        "inactive": "Ce compte est désactivé. Contactez Satkaar.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].label = "Mot de passe"
        _habiller(self)

    def _cle_essais(self):
        adresse = self.request.META.get("REMOTE_ADDR", "") if self.request else ""
        courriel = (self.data.get("username") or "").strip().lower()
        return f"connexion:{adresse}:{courriel}"

    def clean(self):
        cle = self._cle_essais()
        if cache.get(cle, 0) >= ESSAIS_MAX:
            raise forms.ValidationError(
                "Trop de tentatives de connexion. Réessayez dans quelques minutes.",
                code="trop_de_tentatives",
            )
        try:
            donnees = super().clean()
        except forms.ValidationError:
            cache.add(cle, 0, FENETRE_ESSAIS)
            cache.incr(cle)
            raise
        cache.delete(cle)
        return donnees


class ReinitialisationForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "Courriel"
        _habiller(self)


class NouveauMotDePasseForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _habiller(self)


class ChangementMotDePasseForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _habiller(self)
