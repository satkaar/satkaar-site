from django.contrib import admin

from .models import DemandeDemonstration


@admin.register(DemandeDemonstration)
class DemandeDemonstrationAdmin(admin.ModelAdmin):
    list_display = ("nom", "collectivite", "fonction", "courriel", "cree_le", "traitee")
    list_filter = ("traitee", "cree_le")
    search_fields = ("nom", "collectivite", "courriel", "message")
    list_editable = ("traitee",)
    readonly_fields = ("cree_le",)
