from django.contrib import admin

from .models import DemandeDemonstration


@admin.register(DemandeDemonstration)
class DemandeDemonstrationAdmin(admin.ModelAdmin):
    list_display = (
        "nom", "organisation", "sujet", "fonction", "courriel", "telephone",
        "rappel_jour", "rappel_heure", "cree_le", "traitee",
    )
    list_filter = ("traitee", "sujet", "cree_le")
    search_fields = ("nom", "organisation", "courriel", "message")
    list_editable = ("traitee",)
    readonly_fields = ("cree_le",)

