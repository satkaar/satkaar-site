from django.contrib import admin

from .models import Document, Projet


class DocumentEnLigne(admin.TabularInline):
    model = Document
    extra = 0
    fields = ("titre", "categorie", "fichier", "ajoute_le")
    readonly_fields = ("ajoute_le",)


@admin.register(Projet)
class ProjetAdmin(admin.ModelAdmin):
    list_display = ("titre", "client", "type", "statut", "avancement", "mis_a_jour")
    list_filter = ("type", "statut")
    search_fields = ("titre", "client__email", "client__last_name")
    autocomplete_fields = ("client",)
    inlines = [DocumentEnLigne]

    def save_formset(self, request, form, formset, change):
        # Les documents ajoutés depuis un projet appartiennent au client de ce projet.
        for document in formset.save(commit=False):
            document.client = form.instance.client
            document.save()
        formset.save_m2m()
        for supprime in formset.deleted_objects:
            supprime.delete()


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("titre", "client", "categorie", "projet", "ajoute_le")
    list_filter = ("categorie",)
    search_fields = ("titre", "client__email")
    autocomplete_fields = ("client", "projet")
