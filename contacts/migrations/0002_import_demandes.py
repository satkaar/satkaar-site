from django.db import migrations


def importer_demandes(apps, schema_editor):
    """Les demandes déjà reçues sur le site deviennent des leads."""
    from contacts.import_demandes import importer

    Demande = apps.get_model("pages", "DemandeDemonstration")
    Contact, Note = apps.get_model("contacts", "Contact"), apps.get_model("contacts", "Note")
    for demande in Demande.objects.order_by("cree_le"):
        importer(demande, Contact, Note)


class Migration(migrations.Migration):
    dependencies = [("contacts", "0001_initial"), ("pages", "0005_sujet_formation")]

    operations = [migrations.RunPython(importer_demandes, migrations.RunPython.noop)]
