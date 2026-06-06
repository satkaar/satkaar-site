from django.contrib import admin

from .models import MessageContact


@admin.register(MessageContact)
class MessageContactAdmin(admin.ModelAdmin):
    list_display = ("cree_le", "nom", "fonction", "commune", "email", "traite")
    list_filter = ("traite", "cree_le")
    list_editable = ("traite",)
    search_fields = ("nom", "email", "commune", "message")
    readonly_fields = ("cree_le",)
    date_hierarchy = "cree_le"
