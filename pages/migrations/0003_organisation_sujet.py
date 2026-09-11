from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0002_rappel_souhaite"),
    ]

    operations = [
        migrations.RenameField(
            model_name="demandedemonstration",
            old_name="collectivite",
            new_name="organisation",
        ),
        migrations.AlterField(
            model_name="demandedemonstration",
            name="organisation",
            field=models.CharField(max_length=160, verbose_name="organisation"),
        ),
        migrations.AddField(
            model_name="demandedemonstration",
            name="sujet",
            field=models.CharField(
                choices=[
                    ("conseil", "Conseil (IA, data, systèmes d'information)"),
                    ("isidor", "Isidor — agriculture"),
                    ("vanessa", "Vanessa — mairies"),
                    ("bernard", "Bernard — immobilier"),
                    ("autre", "Autre demande"),
                ],
                default="autre",
                max_length=20,
                verbose_name="sujet",
            ),
        ),
        migrations.AlterModelOptions(
            name="demandedemonstration",
            options={
                "ordering": ["-cree_le"],
                "verbose_name": "demande de contact",
                "verbose_name_plural": "demandes de contact",
            },
        ),
    ]
