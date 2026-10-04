"""
Catalogue sémantique et terminologique pour GéoFoncier V2 (Contextual Terminology).

Définit le vocabulaire métier adapté selon le Type d'espace (Commune, Campus Universitaire,
Direction du Cadastre, Périmètre Étatique, Zone Économique/Autre).
"""

from typing import Dict, Any

# Catalogue canonique des termes par type d'espace
TERMINOLOGY_CATALOG: Dict[str, Dict[str, str]] = {
    'commune': {
        # Sol & Foncier
        'sol_label': 'Parcelle',
        'sol_plural': 'Parcelles',
        'sol_desc': 'Parcelles coutumières, lotissements et terres cultivables.',

        # Bâti & Constructions
        'bati_label': 'Concession / Maison',
        'bati_plural': 'Concessions',
        'bati_desc': 'Ensembles bâtis, concessions familiales et maisons individuelles.',

        # Occupation & Usagers
        'occupant_label': 'Chef de ménage',
        'occupant_plural': 'Ménages & Occupants',
        'occupant_desc': 'Familles, chefs de concessions et résidents recensés.',

        # Découpage administratif
        'zone_label': 'Village / Quartier',
        'zone_plural': 'Villages & Quartiers',
        'zone_desc': 'Subdivisions territoriales locales et localités communales.',

        # Voiries & Réseaux
        'reseau_label': 'Piste / Voie de desserte',
        'reseau_plural': 'Routes & Pistes rurales',
        'reseau_desc': 'Pistes en latérite, routes communales et voies de desserte.',

        # Projets & Aménagement
        'projet_label': 'Autorisation de construire',
        'projet_plural': 'Permis & Projets de construction',
        'projet_desc': 'Instructions de nouvelles constructions et conformité au PDU.',

        # Autorité & Gouvernance
        'autorite_label': 'Maire & Commission domaniale',
        'gestionnaire_label': 'Agent communal / Gestionnaire foncier',
    },

    'universite': {
        # Sol & Foncier
        'sol_label': 'Emprise foncière',
        'sol_plural': 'Emprises & Terrains',
        'sol_desc': 'Titre foncier universitaire, réserves pédagogiques et parcelles de recherche.',

        # Bâti & Constructions
        'bati_label': 'Bâtiment / Pavillon',
        'bati_plural': 'Bâtiments & Pavillons',
        'bati_desc': 'Amphithéâtres, laboratoires, blocs pédagogiques et résidences universitaires.',

        # Occupation & Usagers
        'occupant_label': 'Affectataire / UFR',
        'occupant_plural': 'UFR & Départements',
        'occupant_desc': 'Unités de formation, instituts, laboratoires et services administratifs.',

        # Découpage administratif
        'zone_label': 'Secteur de campus',
        'zone_plural': 'Secteurs du Campus',
        'zone_desc': 'Campus principal, zone pédagogique, zone sportive et pôle hébergement.',

        # Voiries & Réseaux
        'reseau_label': 'Voirie / Allée piétonne',
        'reseau_plural': 'Voiries & Allées du campus',
        'reseau_desc': 'Voiries bitumées, allées piétonnes, voies carrossables et réseaux.',

        # Projets & Aménagement
        'projet_label': 'Projet d\'extension',
        'projet_plural': 'Chantiers & Extensions académiques',
        'projet_desc': 'Construction de nouveaux amphithéâtres, laboratoires et réhabilitations.',

        # Autorité & Gouvernance
        'autorite_label': 'Rectorat & Direction du Patrimoine',
        'gestionnaire_label': 'Technicien DPL / Responsable patrimoine',
    },

    'cadastre': {
        # Sol & Foncier
        'sol_label': 'Parcelle cadastrale (NICAD)',
        'sol_plural': 'Parcelles cadastrales',
        'sol_desc': 'Parcelles géoréférencées avec numéro d\'identification officiel et bornes UTM.',

        # Bâti & Constructions
        'bati_label': 'Bâti immatriculé',
        'bati_plural': 'Bâtis & Immeubles',
        'bati_desc': 'Emprises bâties immatriculées au livre foncier.',

        # Occupation & Usagers
        'occupant_label': 'Titulaire du droit / Propriétaire',
        'occupant_plural': 'Propriétaires & Titulaires de baux',
        'occupant_desc': 'Bénéficiaires de titres fonciers, baux emphytéotiques ou concessions.',

        # Découpage administratif
        'zone_label': 'Section cadastrale',
        'zone_plural': 'Sections cadastrales',
        'zone_desc': 'Découpage géodésique officiel du cadastre national.',

        # Voiries & Réseaux
        'reseau_label': 'Emprise de voirie publique',
        'reseau_plural': 'Voies publiques & Réseaux',
        'reseau_desc': 'Alignements, voies classées et servitudes de passage cadastrées.',

        # Projets & Aménagement
        'projet_label': 'Mutation / Morcellement',
        'projet_plural': 'Opérations cadastrales & Mutations',
        'projet_desc': 'Bornages, fusions, divisions de parcelles et transferts de droits.',

        # Autorité & Gouvernance
        'autorite_label': 'Conservation foncière & Cadastre',
        'gestionnaire_label': 'Géomètre-expert / Inspecteur du cadastre',
    },

    'ministere': {
        # Sol & Foncier
        'sol_label': 'Emprise domaniale',
        'sol_plural': 'Emprises domaniales',
        'sol_desc': 'Domaine public et privé de l\'État, réserves foncières ministérielles.',

        # Bâti & Constructions
        'bati_label': 'Édifice public / Ouvrage',
        'bati_plural': 'Édifices publics & Ouvrages',
        'bati_desc': 'Bâtiments administratifs ministériels, infrastructures et équipements d\'État.',

        # Occupation & Usagers
        'occupant_label': 'Direction affectataire',
        'occupant_plural': 'Directions & Agences de l\'État',
        'occupant_desc': 'Services étatiques, ministères délégataires et établissements publics.',

        # Découpage administratif
        'zone_label': 'Circonscription / Arrondissement',
        'zone_plural': 'Circonscriptions territoriales',
        'zone_desc': 'Découpage administratif étatique ou périmètre d\'intervention national.',

        # Voiries & Réseaux
        'reseau_label': 'Axe routier national / Réseau',
        'reseau_plural': 'Infrastructures de transport & Réseaux',
        'reseau_desc': 'Réseau routier national, autoroutes et grandes infrastructures.',

        # Projets & Aménagement
        'projet_label': 'Grand projet d\'État',
        'projet_plural': 'Grands chantiers & Aménagements',
        'projet_desc': 'Infrastructures régaliennes, pôles urbains étatiques et schémas directeurs.',

        # Autorité & Gouvernance
        'autorite_label': 'Ministère de tutelle / DGID',
        'gestionnaire_label': 'Chargé de mission domaniale',
    },

    'autre': {
        # Sol & Foncier
        'sol_label': 'Lot / Parcelle',
        'sol_plural': 'Lots fonciers',
        'sol_desc': 'Unités de terrain et assiettes foncières.',

        # Bâti & Constructions
        'bati_label': 'Unité bâtie',
        'bati_plural': 'Unités bâties',
        'bati_desc': 'Installations, bâtiments et hangars.',

        # Occupation & Usagers
        'occupant_label': 'Occupant / Gestionnaire',
        'occupant_plural': 'Occupants & Gestionnaires',
        'occupant_desc': 'Personnes physiques ou morales exploitant le site.',

        # Découpage administratif
        'zone_label': 'Secteur',
        'zone_plural': 'Secteurs & Pôles',
        'zone_desc': 'Zones d\'activités ou sous-ensembles géographiques.',

        # Voiries & Réseaux
        'reseau_label': 'Réseau linéaire',
        'reseau_plural': 'Réseaux linéaires & Voies',
        'reseau_desc': 'Réseaux de circulation, canalisations et dessertes internes.',

        # Projets & Aménagement
        'projet_label': 'Projet d\'aménagement',
        'projet_plural': 'Projets & Chantiers',
        'projet_desc': 'Travaux, aménagements et opérations de développement.',

        # Autorité & Gouvernance
        'autorite_label': 'Direction gestionnaire',
        'gestionnaire_label': 'Opérateur territorial',
    }
}

# Valeurs par défaut universelles en cas d'omission
DEFAULT_TERMS: Dict[str, str] = {
    'sol_label': 'Parcelle',
    'sol_plural': 'Parcelles',
    'sol_desc': 'Unités foncières et parcelles.',
    'bati_label': 'Bâtiment / Concession',
    'bati_plural': 'Bâtiments',
    'bati_desc': 'Constructions et unités d\'habitation.',
    'occupant_label': 'Occupant / Résident',
    'occupant_plural': 'Occupants & Résidents',
    'occupant_desc': 'Personnes ou entités occupant le lieu.',
    'zone_label': 'Secteur / Localité',
    'zone_plural': 'Secteurs & Localités',
    'zone_desc': 'Sous-secteurs territoriaux.',
    'reseau_label': 'Réseau linéaire',
    'reseau_plural': 'Réseaux linéaires',
    'reseau_desc': 'Réseaux et voiries de transport.',
    'projet_label': 'Projet de construction',
    'projet_plural': 'Projets de construction',
    'projet_desc': 'Autorisations et chantiers.',
    'autorite_label': 'Autorité gestionnaire',
    'gestionnaire_label': 'Gestionnaire',
}
