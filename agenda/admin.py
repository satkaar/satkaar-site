from django.contrib import admin

from .models import Evenement


@admin.register(Evenement)
class EvenementAdmin(admin.ModelAdmin):
    list_display = ("titre", "categorie", "debut", "fin", "organisation")
    list_filter = ("categorie",)
    search_fields = ("titre", "organisation", "lieu")
    date_hierarchy = "debut"
    filter_horizontal = ("participants",)
