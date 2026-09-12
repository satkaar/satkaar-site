from django.contrib import admin

from .models import CompteCourriel, Courriel, PieceJointe


@admin.register(CompteCourriel)
class CompteCourrielAdmin(admin.ModelAdmin):
    list_display = ("adresse", "libelle", "imap_hote", "actif", "derniere_releve", "derniere_erreur")
    # Le mot de passe se saisit dans l'espace (Mail › Gérer les boîtes), où il est chiffré.
    exclude = ("mot_de_passe_chiffre",)


class PieceJointeEnLigne(admin.TabularInline):
    model = PieceJointe
    extra = 0
    readonly_fields = ("nom", "type_mime", "taille")


@admin.register(Courriel)
class CourrielAdmin(admin.ModelAdmin):
    list_display = ("sujet", "expediteur_adresse", "compte", "dossier", "date", "lu", "corbeille")
    list_filter = ("compte", "dossier", "lu", "corbeille")
    search_fields = ("sujet", "expediteur_adresse", "destinataires")
    inlines = [PieceJointeEnLigne]
