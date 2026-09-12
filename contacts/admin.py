from django.contrib import admin

from .models import Contact, Note


class NoteEnLigne(admin.TabularInline):
    model = Note
    extra = 0
    readonly_fields = ("cree_le",)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("nom", "organisation", "produit", "statut", "prochaine_relance", "responsable")
    list_filter = ("produit", "statut", "source")
    search_fields = ("nom", "organisation", "courriel", "ville")
    inlines = [NoteEnLigne]
