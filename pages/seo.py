"""Référencement (SEO) et moteurs de réponse par IA (GEO).

Une seule source pour les FAQ, les fils d'Ariane et les fiches schema.org : ce qui est affiché
et ce qui est déclaré aux moteurs ne peuvent pas diverger. N'y écrire que des faits déjà
présents sur le site.
"""

from django.templatetags.static import static
from django.urls import reverse

NOM = "Satkaar"
TELEPHONE = "+33634618697"
COURRIEL = "contact@satkaar.io"
LINKEDIN_FONDATEUR = "https://www.linkedin.com/in/damienmarque/"


def absolue(request, chemin):
    return request.build_absolute_uri(chemin)


# --- Organisation ---------------------------------------------------------------------------

def organisation(request):
    """Satkaar, ses deux implantations et son fondateur (schema.org)."""
    racine = absolue(request, "/")
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": racine + "#organisation",
                "name": NOM,
                "url": racine,
                "logo": absolue(request, static("img/partage/logo-satkaar.png")),
                "description": (
                    "Groupe français qui réunit le conseil en intelligence artificielle, data et "
                    "systèmes d'information, l'édition de quatre logiciels métier (Isidor, Katarina, "
                    "Vanessa, Bernard) et la formation certifiée Qualiopi."
                ),
                "email": COURRIEL,
                "telephone": TELEPHONE,
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "67 chemin Auguste Girard",
                    "postalCode": "04100",
                    "addressLocality": "Manosque",
                    "addressRegion": "Provence-Alpes-Côte d'Azur",
                    "addressCountry": "FR",
                },
                "areaServed": ["Alpes-de-Haute-Provence", "Bouches-du-Rhône", "Provence-Alpes-Côte d'Azur"],
                "founder": {"@id": racine + "#fondateur"},
                "knowsAbout": [
                    "Intelligence artificielle", "Data", "Architecture des systèmes d'information",
                    "Machine learning", "MLOps", "Prédiction", "Gouvernance des données", "RGPD",
                    "Règlement européen sur l'IA", "Cybersécurité", "Conduite du changement",
                ],
                "hasCredential": {
                    "@type": "EducationalOccupationalCredential",
                    "name": "Certification Qualiopi — actions de formation",
                },
                "contactPoint": {
                    "@type": "ContactPoint",
                    "contactType": "service commercial",
                    "telephone": TELEPHONE,
                    "email": COURRIEL,
                    "areaServed": "FR",
                    "availableLanguage": "French",
                },
            },
            {
                "@type": "ProfessionalService",
                "@id": racine + "#manosque",
                "name": f"{NOM} — Manosque",
                "parentOrganization": {"@id": racine + "#organisation"},
                "url": racine,
                "telephone": TELEPHONE,
                "image": absolue(request, static("img/partage/satkaar-partage.png")),
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "67 chemin Auguste Girard",
                    "postalCode": "04100",
                    "addressLocality": "Manosque",
                    "addressCountry": "FR",
                },
                # Coordonnées du centre de la commune, pas de l'adresse exacte.
                "geo": {"@type": "GeoCoordinates", "latitude": 43.8337, "longitude": 5.7836},
                "areaServed": ["Alpes-de-Haute-Provence", "Provence-Alpes-Côte d'Azur"],
            },
            {
                "@type": "ProfessionalService",
                "@id": racine + "#aix-en-provence",
                "name": f"{NOM} — Aix-en-Provence",
                "parentOrganization": {"@id": racine + "#organisation"},
                "url": racine,
                "telephone": TELEPHONE,
                "image": absolue(request, static("img/partage/satkaar-partage.png")),
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "Aix-en-Provence",
                    "postalCode": "13100",
                    "addressCountry": "FR",
                },
                "geo": {"@type": "GeoCoordinates", "latitude": 43.5297, "longitude": 5.4474},
                "areaServed": ["Bouches-du-Rhône", "Provence-Alpes-Côte d'Azur"],
            },
            {
                "@type": "Person",
                "@id": racine + "#fondateur",
                "name": "Damien Marque",
                "jobTitle": "Fondateur et CEO",
                "worksFor": {"@id": racine + "#organisation"},
                "alumniOf": "Grenoble INP – Ensimag",
                "sameAs": [LINKEDIN_FONDATEUR],
            },
            {
                "@type": "WebSite",
                "@id": racine + "#site",
                "name": NOM,
                "url": racine,
                "inLanguage": "fr-FR",
                "publisher": {"@id": racine + "#organisation"},
            },
        ],
    }


# --- Fil d'Ariane ----------------------------------------------------------------------------

def fil_ariane(request, etapes):
    """etapes : liste de (libellé, nom d'URL). L'accueil est ajouté en tête."""
    elements = [("Accueil", "pages:accueil")] + list(etapes)
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": rang, "name": libelle, "item": absolue(request, reverse(nom))}
            for rang, (libelle, nom) in enumerate(elements, 1)
        ],
    }


# --- Logiciels -------------------------------------------------------------------------------

LOGICIELS = {
    "isidor": {
        "name": "Isidor",
        "description": (
            "Assistant agricole français qui retient, calcule et prouve à la place de l'agriculteur : "
            "irrigation, charges et marges, traçabilité, équipe, conformité réglementaire, à l'écrit "
            "comme à la voix."
        ),
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web, iOS, Android",
        "image": "img/produits/isidor-tableau-de-bord.webp",
        "offers": {
            "@type": "Offer",
            "price": "29.90",
            "priceCurrency": "EUR",
            "description": "29,90 € HT par mois et par exploitation, plus 0,33 € HT par hectare et par mois.",
        },
    },
    "katarina": {
        "name": "Katarina",
        "description": (
            "Logiciel des chambres d'agriculture : suivi des tâches des équipes et saisie optimisée, "
            "pour moins de ressaisie et plus de temps sur le terrain."
        ),
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web",
        "image": "img/produits/katarina-taches.webp",
    },
    "vanessa": {
        "name": "Vanessa",
        "description": (
            "Application des mairies : les habitants signalent un problème, réservent une salle ou "
            "suivent une démarche depuis leur téléphone, et sont informés à chaque étape."
        ),
        "applicationCategory": "GovernmentApplication",
        "operatingSystem": "iOS, Android",
        "image": "img/produits/vanessa-suivi.webp",
    },
    "bernard": {
        "name": "Bernard",
        "description": (
            "Logiciel de gestion immobilière, du mandat à la quittance : portefeuille de biens, "
            "gestion locative, annonces et un espace par métier."
        ),
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web",
        "image": "img/produits/bernard-portefeuille.webp",
    },
}


def logiciel(request, cle):
    donnees = dict(LOGICIELS[cle])
    image = donnees.pop("image")
    racine = absolue(request, "/")
    return {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        **donnees,
        "url": absolue(request, reverse(f"pages:{cle}")),
        "image": absolue(request, static(image)),
        "inLanguage": "fr-FR",
        "publisher": {"@type": "Organization", "@id": racine + "#organisation", "name": NOM},
    }


# --- FAQ -------------------------------------------------------------------------------------
# Réponses courtes, qui commencent par l'essentiel : c'est ce que reprennent les moteurs de
# réponse. Chaque liste est affichée sur sa page et déclarée en FAQPage.

FAQ = {
    "accueil": [
        ("Qu'est-ce que Satkaar ?",
         "Satkaar est un groupe français présent à Manosque (Alpes-de-Haute-Provence) et à "
         "Aix-en-Provence (Bouches-du-Rhône). Il réunit trois métiers : le conseil en intelligence "
         "artificielle, data et systèmes d'information ; l'édition de quatre logiciels métier "
         "(Isidor, Katarina, Vanessa et Bernard) ; et la formation, certifiée Qualiopi."),
        ("Où intervient Satkaar ?",
         "Satkaar reçoit ses clients dans ses bureaux de Manosque et d'Aix-en-Provence, ou se déplace "
         "chez eux, en Provence-Alpes-Côte d'Azur."),
        ("Qui a fondé Satkaar ?",
         "Satkaar a été fondé par Damien Marque, ingénieur diplômé de Grenoble INP – Ensimag. Il a "
         "mené près de dix ans de projets data et IA pour de grands groupes, dont BNP Paribas, le "
         "Groupement Les Mousquetaires, Auchan Retail, Adeo et Geopost."),
        ("Comment démarrer un projet avec Satkaar ?",
         "Par un premier échange de trente minutes, sans engagement, à demander depuis la page "
         "Contact ou au 06 34 61 86 97. Vous pouvez choisir le jour et l'heure auxquels être rappelé."),
    ],
    "conseil": [
        ("Quelles expertises propose le conseil de Satkaar ?",
         "Dix expertises : stratégie et feuille de route, intelligence artificielle, data, "
         "architecture des systèmes d'information, tech, ML engineering, prédiction, gouvernance et "
         "conformité, cybersécurité, et conduite du changement."),
        ("Comment se déroule une mission de conseil ?",
         "En quatre temps : un cadrage sur le terrain, la conception (architecture, choix des "
         "modèles, prototype sur vos données), la mise en production dans vos systèmes, puis la "
         "transmission aux équipes, avec formation et suivi."),
        ("Faut-il utiliser les logiciels de Satkaar pour faire appel au conseil ?",
         "Non. Le conseil est un métier à part entière : Satkaar intervient sur un point précis ou "
         "sur l'ensemble d'un projet, que vous utilisiez ses logiciels ou non."),
        ("Satkaar accompagne-t-il la conformité au RGPD et au règlement européen sur l'IA ?",
         "Oui. L'expertise gouvernance et conformité couvre le règlement européen sur l'IA, le RGPD "
         "et la souveraineté des données : cadrer les usages, documenter les modèles, rester conforme."),
        ("Où se trouvent les consultants de Satkaar ?",
         "À Manosque, dans les Alpes-de-Haute-Provence, et à Aix-en-Provence, dans les "
         "Bouches-du-Rhône. Ils interviennent chez leurs clients en Provence-Alpes-Côte d'Azur."),
    ],
    "formation": [
        ("Satkaar est-il un organisme de formation certifié Qualiopi ?",
         "Oui. La certification qualité a été délivrée à Satkaar au titre de la catégorie d'actions "
         "suivante : actions de formation."),
        ("Les formations de Satkaar sont-elles finançables ?",
         "La certification Qualiopi permet la prise en charge des formations par les financements "
         "publics et mutualisés, notamment ceux des opérateurs de compétences (OPCO)."),
        ("Quelles formations propose Satkaar ?",
         "Trois parcours : l'IA et la data au quotidien pour les équipes, le pilotage d'un projet IA "
         "ou data pour les dirigeants et managers, et la prise en main des logiciels Isidor, "
         "Katarina, Vanessa et Bernard."),
        ("Les formations ont-elles lieu sur site ou à distance ?",
         "Les deux : le programme, les objectifs et la durée sont adaptés à chaque demande, sur site "
         "ou à distance, en petits groupes."),
        ("Les formations sont-elles accessibles aux personnes en situation de handicap ?",
         "Oui. Signalez vos besoins avant la formation : les supports, le rythme et les modalités "
         "sont adaptés."),
    ],
    "logiciels": [
        ("Quels logiciels édite Satkaar ?",
         "Quatre logiciels métier : Isidor pour les agriculteurs, Katarina pour les chambres "
         "d'agriculture, Vanessa pour les mairies et Bernard pour la gestion immobilière."),
        ("Combien coûte Isidor ?",
         "29,90 € HT par mois et par exploitation, plus 0,33 € HT par hectare et par mois, "
         "utilisateurs illimités et sans engagement."),
        ("Où sont hébergées les données d'Isidor ?",
         "En France. Elles ne sont jamais revendues et restent exportables à tout moment."),
        ("Quelles communes utilisent Vanessa ?",
         "Vanessa est en finalisation de tests à Forcalquier et à Manosque, et en cours de "
         "déploiement à Pierrevert, Villeneuve et Sisteron, dans les Alpes-de-Haute-Provence."),
        ("Comment voir un logiciel Satkaar en fonctionnement ?",
         "Par une démonstration de trente minutes, sans engagement, à demander depuis la page "
         "Contact."),
    ],
}


def faq(request, cle):
    questions = FAQ[cle]
    return {
        "questions": questions,
        "jsonld": {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": r}}
                for q, r in questions
            ],
        },
    }
