"""Chaque demande déposée sur le site devient un lead (ou s'ajoute à la fiche existante)."""

PRODUITS = {"isidor", "vanessa", "bernard", "katarina", "conseil", "formation"}


def importer(demande, Contact, Note):
    produit = demande.sujet if demande.sujet in PRODUITS else "autre"
    existant = None
    if demande.courriel:
        existant = Contact.objects.filter(courriel__iexact=demande.courriel, produit=produit).first()
    resume = f"Demande reçue sur le site ({demande.get_sujet_display() if hasattr(demande, 'get_sujet_display') else demande.sujet})"
    if demande.message:
        resume += f" :\n{demande.message}"
    if existant:
        existant.demande_id = existant.demande_id or demande.pk
        if demande.rappel_jour:
            existant.prochaine_relance = demande.rappel_jour
        existant.save()
        Note.objects.create(contact=existant, type="note", texte=resume)
        return existant
    contact = Contact.objects.create(
        nom=demande.nom, organisation=demande.organisation, fonction=demande.fonction, courriel=demande.courriel,
        telephone=demande.telephone, produit=produit, statut="lead", source="site", demande_id=demande.pk,
        prochaine_relance=demande.rappel_jour,
    )
    Note.objects.create(contact=contact, type="note", texte=resume)
    return contact
