"""
Services métier pour l'instruction et l'analyse de faisabilité des constructions.
Gestion des contraintes spatiales, calculs de superficies constructibles,
propositions d'alternatives et aide à la décision multicritère.
"""
import json
from django.db.models import Q
from dossiers.models import Dossier, ZoneSecteur, UniteBatie, ReseauLineaire

UTM_SRID = 32628


def to_utm(geom):
    """Clone et projette une géométrie en UTM 28N (EPSG:32628)."""
    return geom.transform(UTM_SRID, clone=True) if geom else None


def nearest_distance_m(point_utm, objets):
    """Plus courte distance (en mètres) entre un point UTM et une liste d'objets géoréférencés."""
    best = None
    for obj in objets:
        geom = getattr(obj, 'geometrie', None)
        if not geom:
            continue
        d = point_utm.distance(to_utm(geom))
        if best is None or d < best:
            best = d
    return best


def calculer_pks_pour_espace(espace, statuts=None, exclude_pk=None):
    """
    Retourne l'ensemble des IDs des projets de construction qui consomment cet espace,
    par sélection directe ou intersection géométrique.
    """
    from urbanisme.models import NouvelleConstruction

    statuts = statuts or NouvelleConstruction.STATUTS_ENGAGES
    base = NouvelleConstruction.objects.filter(statut__in=statuts)
    if exclude_pk:
        base = base.exclude(pk=exclude_pk)

    pks = set(base.filter(zone_secteur=espace).values_list('pk', flat=True))
    if getattr(espace, 'geometrie', None):
        pks.update(
            base.filter(
                zone_souhaitee__isnull=False,
                zone_souhaitee__intersects=espace.geometrie,
            ).values_list('pk', flat=True)
        )
    return pks


def calculer_superficie_allouee_espace(espace, statuts=None, exclude_pk=None):
    """Calcule le cumul des superficies souhaitées engagées sur un espace."""
    from urbanisme.models import NouvelleConstruction

    pks = calculer_pks_pour_espace(espace, statuts=statuts, exclude_pk=exclude_pk)
    if not pks:
        return 0.0
    return sum(
        c.superficie_souhaitee or 0
        for c in NouvelleConstruction.objects.filter(pk__in=pks)
    )


def trouver_alternatives_projet(projet):
    """Cherche des zones constructibles disposant d'assez de superficie nette."""
    from urbanisme.models import NouvelleConstruction

    candidates = ZoneSecteur.objects.filter(
        type_zone__in=[
            ZoneSecteur.TYPE_ESPACE_LIBRE,
            ZoneSecteur.TYPE_SECTEUR_CAMPUS,
            ZoneSecteur.TYPE_ZONE_ACTIVITE,
        ],
        superficie_m2__gte=projet.superficie_souhaitee,
    ).order_by('superficie_m2')

    valides = []
    for esp in candidates:
        taux_occ = getattr(esp, 'taux_occupation', 40.0) or 40.0
        constructible = (esp.superficie_m2 or 0) * (taux_occ / 100)
        eng = calculer_superficie_allouee_espace(esp, exclude_pk=projet.pk)
        batie = sum(ub.emprise_sol_m2 or 0 for ub in esp.unites_baties.all()) if hasattr(esp, 'unites_baties') else 0
        nette = max(0.0, constructible - eng - batie)
        if nette >= (projet.superficie_souhaitee or 0):
            valides.append((esp, nette))
        if len(valides) >= 6:
            break

    if valides:
        projet.zones_alternatives = ', '.join(
            f"{e.nom} ({nette:,.0f} m² nets disponibles)"
            for e, nette in valides
        )
        return ZoneSecteur.objects.filter(pk__in=[e.pk for e, _ in valides])

    projet.zones_alternatives = "Aucune zone alternative disponible avec superficie suffisante."
    return ZoneSecteur.objects.none()


def rejeter_projets_concurrents(projet):
    """
    Appelé après approbation d'une construction.
    Parcourt toutes les demandes concurrentes en attente sur la zone et rejette
    automatiquement celles devenues irréalisables par manque de superficie nette restante.
    """
    from urbanisme.models import NouvelleConstruction

    if projet.statut not in NouvelleConstruction.STATUTS_ENGAGES:
        return []

    # Zone de référence
    if projet.zone_secteur and getattr(projet.zone_secteur, 'geometrie', None):
        zone_ref = projet.zone_secteur.geometrie
    elif projet.zone_souhaitee:
        zone_ref = projet.zone_souhaitee
    else:
        return []

    qs_attente = NouvelleConstruction.objects.filter(
        statut=NouvelleConstruction.STATUT_EN_COURS,
        zone_souhaitee__intersects=zone_ref,
    ).exclude(pk=projet.pk)

    auto_rejetees = []

    for concurrent in qs_attente:
        if concurrent.zone_secteur and getattr(concurrent.zone_secteur, 'geometrie', None):
            zone_concurrent = concurrent.zone_secteur.geometrie
        elif concurrent.zone_souhaitee:
            zone_concurrent = concurrent.zone_souhaitee
        else:
            continue

        espaces_libres = ZoneSecteur.objects.filter(
            type_zone__in=[ZoneSecteur.TYPE_ESPACE_LIBRE, ZoneSecteur.TYPE_SECTEUR_CAMPUS, ZoneSecteur.TYPE_ZONE_ACTIVITE],
            geometrie__intersects=zone_concurrent,
        )
        sup_constructible = sum(
            (e.superficie_m2 or 0) * (getattr(e, 'taux_occupation', 40) / 100) for e in espaces_libres
        )
        sup_engagee = sum(
            calculer_superficie_allouee_espace(e, exclude_pk=concurrent.pk)
            for e in espaces_libres
        )
        sup_batie = sum(
            sum(ub.emprise_sol_m2 or 0 for ub in e.unites_baties.all()) if hasattr(e, 'unites_baties') else 0
            for e in espaces_libres
        )
        sup_nette = max(0.0, sup_constructible - sup_engagee - sup_batie)
        sup_brute = sum(e.superficie_m2 or 0 for e in espaces_libres)
        taux_moy = (sup_constructible / sup_brute * 100) if sup_brute else projet.TAUX_OCCUPATION_MAX * 100

        if sup_nette < (concurrent.superficie_souhaitee or 0):
            date_str = projet.updated_at.strftime('%d/%m/%Y') if hasattr(projet, 'updated_at') else ''
            note = (
                f"\n[Rejet automatique le {date_str}] "
                f"La construction « {projet.nom_projet} » a été approuvée "
                f"et occupe {projet.superficie_souhaitee:.0f} m² dans cette zone. "
                f"Superficie constructible ({taux_moy:.0f}%) : {sup_constructible:.0f} m², "
                f"nette restante : {sup_nette:.0f} m², "
                f"insuffisante pour ce projet ({concurrent.superficie_souhaitee:.0f} m² requis)."
            )
            concurrent.statut = NouvelleConstruction.STATUT_REJETE
            concurrent.rapport_faisabilite = (concurrent.rapport_faisabilite or '') + note
            concurrent.disponible = False
            concurrent.save(update_fields=['statut', 'rapport_faisabilite', 'disponible'])
            auto_rejetees.append(concurrent)

    return auto_rejetees


def analyser_disponibilite_projet(projet):
    """
    Analyse de faisabilité et de disponibilité spatiale pour un projet de construction :
    - Évalue l'espace sélectionné ou l'emprise polygonale dessinée
    - Calcule la superficie constructible selon le taux réglementaire
    - Déduit les superficies déjà engagées et existantes
    - Propose des alternatives si non faisable
    Retourne (disponible: bool, rapport: str, alternatives_qs, stats: dict).
    """
    from urbanisme.models import NouvelleConstruction

    alternatives = ZoneSecteur.objects.none()
    sup_requise = projet.superficie_souhaitee or 0

    def _stats_vides(sup_brute=0, espaces_info=None):
        return {
            'espaces': espaces_info or [],
            'taux_moyen': 0,
            'sup_brute': sup_brute,
            'sup_brute_ha': round(sup_brute / 10000, 2),
            'sup_reservee': 0,
            'sup_reservee_ha': 0,
            'sup_construct': 0,
            'sup_construct_ha': 0,
            'sup_engagee': 0,
            'sup_engagee_ha': 0,
            'nb_engagees': 0,
            'sup_batie': 0,
            'sup_batie_ha': 0,
            'sup_occupee': 0,
            'sup_occupee_ha': 0,
            'sup_nette': 0,
            'sup_nette_ha': 0,
            'sup_requise': sup_requise,
            'sup_requise_ha': round(sup_requise / 10000, 2),
            'manque': sup_requise,
            'manque_ha': round(sup_requise / 10000, 2),
            'nb_attente': 0,
            'sup_attente': 0,
            'sup_attente_ha': 0,
            'constructions_engagees': [],
            'pct_engagee': 0,
            'pct_occupee': 0,
            'pct_nette': 0,
            'pct_requise': 100,
        }

    if sup_requise <= 0:
        projet.disponible = False
        projet.rapport_faisabilite = "Erreur : la superficie souhaitée doit être supérieure à 0."
        projet.save()
        return False, projet.rapport_faisabilite, alternatives, _stats_vides()

    # Cas 1 : Zone sélectionnée
    if projet.zone_secteur_id and projet.zone_secteur:
        espace_obj = projet.zone_secteur
        zone_analyse = espace_obj.geometrie
        if espace_obj.type_zone not in (ZoneSecteur.TYPE_ESPACE_LIBRE, ZoneSecteur.TYPE_SECTEUR_CAMPUS, ZoneSecteur.TYPE_ZONE_ACTIVITE):
            projet.disponible = False
            projet.rapport_faisabilite = (
                f"La zone « {espace_obj.nom} » ({espace_obj.code}) n'est pas constructible "
                f"(statut actuel : {espace_obj.get_type_zone_display()})."
            )
            projet.zones_alternatives = ''
            alternatives = trouver_alternatives_projet(projet)
            projet.save()
            return False, projet.rapport_faisabilite, alternatives, _stats_vides(
                sup_brute=espace_obj.superficie_m2 or 0,
                espaces_info=[{'nom': espace_obj.nom, 'code': espace_obj.code,
                               'taux': getattr(espace_obj, 'taux_occupation', 40)}],
            )
        espaces = [espace_obj]

    # Cas 2 : Zone polygonale dessinée
    elif projet.zone_souhaitee:
        zone_analyse = projet.zone_souhaitee
        espaces = list(ZoneSecteur.objects.filter(
            type_zone__in=[ZoneSecteur.TYPE_ESPACE_LIBRE, ZoneSecteur.TYPE_SECTEUR_CAMPUS, ZoneSecteur.TYPE_ZONE_ACTIVITE],
            geometrie__intersects=zone_analyse,
        ))
    else:
        projet.disponible = False
        projet.rapport_faisabilite = "Aucune zone dessinée sur la carte ni zone sélectionnée."
        projet.save()
        return False, projet.rapport_faisabilite, alternatives, _stats_vides()

    if not espaces:
        projet.disponible = False
        projet.rapport_faisabilite = (
            "La zone sélectionnée ne contient aucun espace constructible. "
            "Elle est peut-être réservée, une voirie, ou sa géométrie "
            "ne correspond à aucune zone enregistrée."
        )
        projet.zones_alternatives = ''
        alternatives = trouver_alternatives_projet(projet)
        projet.save()
        return False, projet.rapport_faisabilite, alternatives, _stats_vides()

    sup_brute = sum((e.superficie_m2 or 0) for e in espaces)
    noms_espaces = ', '.join(f"{e.nom} ({getattr(e, 'taux_occupation', 40):.0f}%)" for e in espaces)

    sup_construct = sum((e.superficie_m2 or 0) * (getattr(e, 'taux_occupation', 40) / 100) for e in espaces)
    sup_reservee = sup_brute - sup_construct
    taux_moyen = (sup_construct / sup_brute * 100) if sup_brute else projet.TAUX_OCCUPATION_MAX * 100

    # Engagements existants
    pks_eng = set()
    for e in espaces:
        pks_eng.update(calculer_pks_pour_espace(e, exclude_pk=projet.pk))
    list_eng = list(NouvelleConstruction.objects.filter(pk__in=pks_eng))
    sup_engagee = sum(c.superficie_souhaitee or 0 for c in list_eng)
    nb_engagees = len(list_eng)

    # Demandes en attente
    qs_attente = NouvelleConstruction.objects.filter(
        statut=NouvelleConstruction.STATUT_EN_COURS,
        zone_souhaitee__intersects=zone_analyse,
    )
    if projet.pk:
        qs_attente = qs_attente.exclude(pk=projet.pk)
    sup_attente = sum(c.superficie_souhaitee or 0 for c in qs_attente)
    nb_attente = qs_attente.count()

    # Superficie occupée par le bâti et aménagements
    sup_batie = sum(
        sum(ub.emprise_sol_m2 or 0 for ub in e.unites_baties.all()) if hasattr(e, 'unites_baties') else 0
        for e in espaces
    )
    sup_terrains = sum(getattr(e, 'superficie_terrains', 0) for e in espaces)
    sup_espaces_verts = sum(getattr(e, 'superficie_espaces_verts', 0) for e in espaces)
    sup_batie_totale = sup_batie + sup_terrains + sup_espaces_verts
    sup_occupee = sup_engagee + sup_batie_totale

    # Superficie nette disponible
    sup_nette = max(0.0, sup_construct - sup_occupee)

    lignes = ["=" * 48]
    if sup_nette >= sup_requise:
        projet.disponible = True
        lignes.append("RÉSULTAT : Zone disponible — Faisable")
    else:
        projet.disponible = False
        lignes.append("RÉSULTAT : Zone insuffisante — Non faisable")

    lignes += [
        "=" * 48,
        f"Espace(s) concerné(s) : {noms_espaces}",
        "-" * 48,
        f"Superficie brute              : {sup_brute:>12,.0f} m²  ({sup_brute/10000:.2f} ha)",
        f"Réservée (voiries, espaces verts…) : -{sup_reservee:>8,.0f} m²  ({sup_reservee/10000:.2f} ha)",
        f"Superficie constructible ({taux_moyen:.0f}% moy.) : {sup_construct:>12,.0f} m²  ({sup_construct/10000:.2f} ha)",
    ]

    if nb_engagees > 0:
        lignes.append(
            f"Déjà allouée ({nb_engagees} construction(s))    : -{sup_engagee:>11,.0f} m²  ({sup_engagee/10000:.2f} ha)"
        )

    if sup_batie_totale > 0:
        lignes.append(
            f"Bâti/terrains/espaces verts existants : -{sup_batie_totale:>11,.0f} m²  ({sup_batie_totale/10000:.2f} ha)"
        )

    lignes += [
        f"Superficie nette disponible   : {sup_nette:>12,.0f} m²  ({sup_nette/10000:.2f} ha)",
        f"Superficie requise            : {sup_requise:>12,.0f} m²  ({sup_requise/10000:.2f} ha)",
    ]

    if not projet.disponible:
        manque = sup_requise - sup_nette
        lignes.append(f"Manque                        : {manque:>12,.0f} m²  ({manque/10000:.2f} ha)")

    if nb_attente > 0:
        lignes += [
            "-" * 48,
            f"ATTENTION : {nb_attente} autre(s) demande(s) en attente",
            f"totalisant {sup_attente:,.0f} m² dans cette zone.",
            "La priorité sera accordée selon l'ordre d'approbation.",
            "Si cette demande est approuvée, les concurrentes",
            "incompatibles seront automatiquement rejetées.",
        ]

    if nb_engagees > 0:
        lignes += ["-" * 48, "Constructions engagées dans cette zone :"]
        for c in list_eng:
            lignes.append(f"  • {c.nom_projet} — {c.superficie_souhaitee:,.0f} m² ({c.get_statut_display()})")

    lignes.append("=" * 48)
    projet.rapport_faisabilite = "\n".join(lignes)
    projet.zones_alternatives = ''

    if not projet.disponible:
        alternatives = trouver_alternatives_projet(projet)

    projet.save()

    manque = max(0.0, sup_requise - sup_nette)
    stats = {
        'espaces': [
            {'nom': e.nom, 'code': e.code, 'taux': e.taux_occupation}
            for e in espaces
        ],
        'taux_moyen': round(taux_moyen, 1),
        'sup_brute': sup_brute,
        'sup_brute_ha': round(sup_brute / 10000, 2),
        'sup_reservee': sup_reservee,
        'sup_reservee_ha': round(sup_reservee / 10000, 2),
        'sup_construct': sup_construct,
        'sup_construct_ha': round(sup_construct / 10000, 2),
        'sup_engagee': sup_engagee,
        'sup_engagee_ha': round(sup_engagee / 10000, 2),
        'nb_engagees': nb_engagees,
        'sup_batie': sup_batie_totale,
        'sup_batie_ha': round(sup_batie_totale / 10000, 2),
        'sup_terrains': sup_terrains,
        'sup_espaces_verts': sup_espaces_verts,
        'sup_occupee': sup_occupee,
        'sup_occupee_ha': round(sup_occupee / 10000, 2),
        'sup_nette': sup_nette,
        'sup_nette_ha': round(sup_nette / 10000, 2),
        'sup_requise': sup_requise,
        'sup_requise_ha': round(sup_requise / 10000, 2),
        'manque': manque,
        'manque_ha': round(manque / 10000, 2),
        'nb_attente': nb_attente,
        'sup_attente': sup_attente,
        'sup_attente_ha': round(sup_attente / 10000, 2),
        'constructions_engagees': [
            {
                'nom': c.nom_projet,
                'superficie': c.superficie_souhaitee,
                'statut': c.get_statut_display(),
                'badge': c.badge_couleur,
            }
            for c in list_eng
        ],
        'pct_engagee': min(100.0, round(sup_occupee / sup_construct * 100, 1)) if sup_construct > 0 else 0.0,
        'pct_nette': min(100.0, round(sup_nette / sup_construct * 100, 1)) if sup_construct > 0 else 0.0,
        'pct_requise': min(100.0, round(sup_requise / sup_construct * 100, 1)) if sup_construct > 0 else 100.0,
    }

    return projet.disponible, projet.rapport_faisabilite, alternatives, stats


def recommander_emplacements_implantation(type_construction, superficie_requise, zone_dessinee=None, dossier=None):
    """
    Système d'aide à la décision multicritère pour l'implantation de nouvelles constructions.
    Analyse les espaces libres, évalue les contraintes et attribue un score sur 100.
    """
    from urbanisme.models import NouvelleConstruction

    superficie_requise = superficie_requise or 0
    if not dossier:
        dossier = Dossier.objects.first()

    esp_qs = ZoneSecteur.objects.filter(
        type_zone__in=[
            ZoneSecteur.TYPE_ESPACE_LIBRE,
            ZoneSecteur.TYPE_SECTEUR_CAMPUS,
            ZoneSecteur.TYPE_ZONE_ACTIVITE,
            ZoneSecteur.TYPE_VILLAGE,
            ZoneSecteur.TYPE_QUARTIER,
        ]
    )
    if dossier:
        esp_qs = esp_qs.filter(dossier=dossier)
    espaces_libres = esp_qs.order_by('nom')

    bat_qs = UniteBatie.objects.all()
    voi_qs = ReseauLineaire.objects.all()
    if dossier:
        bat_qs = bat_qs.filter(dossier=dossier)
        voi_qs = voi_qs.filter(dossier=dossier)

    batiments = list(bat_qs)
    voiries = list(voi_qs)
    terrains_sportifs = [b for b in batiments if b.type_bati == UniteBatie.TYPE_SPORTIF]
    espaces_verts = [e for e in espaces_libres if e.type_zone == ZoneSecteur.TYPE_ESPACE_LIBRE]

    resultats = []

    for espace in espaces_libres:
        if not espace.geometrie:
            continue

        raisons, contraintes = [], []
        compatible = True

        if dossier and dossier.emprise and not dossier.emprise.contains(espace.geometrie):
            contraintes.append("Hors du périmètre du Territoire.")
            compatible = False

        if zone_dessinee is not None:
            if not espace.geometrie.contains(zone_dessinee):
                continue
            zone_test = zone_dessinee
        else:
            zone_test = espace.geometrie

        zone_test_utm = to_utm(zone_test)
        superficie_zone = zone_test_utm.area

        def _intersectants(objets):
            return [o for o in objets if getattr(o, 'geometrie', None) and zone_test.intersects(o.geometrie)]

        bat_conf = _intersectants(batiments)
        voi_conf = _intersectants(voiries)
        ter_conf = _intersectants(terrains_sportifs)
        ev_conf = _intersectants(espaces_verts)

        if zone_dessinee is not None:
            if bat_conf:
                contraintes.append(f"Intersecte {len(bat_conf)} bâtiment(s).")
                compatible = False
            if voi_conf:
                contraintes.append(f"Intersecte {len(voi_conf)} voirie(s).")
                compatible = False
            if ter_conf:
                contraintes.append(f"Intersecte {len(ter_conf)} terrain(s) sportif(s).")
                compatible = False
            if ev_conf:
                contraintes.append(f"Intersecte {len(ev_conf)} espace(s) vert(s) protégé(s).")
                compatible = False
            superficie_disponible = superficie_zone if compatible else 0.0
            taux_conflit = 0.0 if compatible else 1.0
        else:
            occupee_geom = None
            for o in (bat_conf + voi_conf + ter_conf + ev_conf):
                occupee_geom = o.geometrie if occupee_geom is None else occupee_geom.union(o.geometrie)
            try:
                zone_libre = zone_test.difference(occupee_geom) if occupee_geom is not None else zone_test
            except Exception:
                zone_libre = zone_test
            superficie_disponible = to_utm(zone_libre).area if zone_libre else 0.0
            taux_conflit = 1 - (superficie_disponible / superficie_zone) if superficie_zone else 1.0

            if bat_conf:
                contraintes.append(f"{len(bat_conf)} bâtiment(s) déjà présent(s) dans l'espace (surface exclue).")
            if voi_conf:
                contraintes.append(f"{len(voi_conf)} voirie(s) traverse(nt) l'espace (surface exclue).")
            if ter_conf:
                contraintes.append(f"{len(ter_conf)} terrain(s) sportif(s) présent(s) (surface exclue).")
            if ev_conf:
                contraintes.append(f"{len(ev_conf)} espace(s) vert(s) protégé(s) présent(s) (surface exclue).")

        if superficie_disponible < superficie_requise:
            contraintes.append(
                f"Superficie disponible insuffisante : {superficie_disponible:,.0f} m² "
                f"pour {superficie_requise:,.0f} m² requis."
            )
            compatible = False
        elif superficie_requise > 0:
            raisons.append(f"Superficie disponible suffisante ({superficie_disponible:,.0f} m²).")

        score_superficie = 30 * min(1.0, superficie_disponible / (superficie_requise * 1.5)) \
            if superficie_requise > 0 else 0.0

        centroid_utm = zone_test_utm.centroid
        dist_voirie = nearest_distance_m(centroid_utm, voiries)
        if dist_voirie is not None:
            score_voirie = 20 * max(0.0, 1 - dist_voirie / 300)
            score_acces = 15 * max(0.0, 1 - dist_voirie / 600)
            if dist_voirie <= 100:
                raisons.append(f"Très proche d'une voirie ({dist_voirie:.0f} m) — bon accès.")
            elif dist_voirie > 400:
                contraintes.append(f"Éloigné des voiries ({dist_voirie:.0f} m) — accès à prévoir.")
        else:
            score_voirie, score_acces = 8.0, 6.0
            contraintes.append("Aucune voirie référencée à proximité pour évaluer l'accès.")

        dist_batiment = nearest_distance_m(centroid_utm, batiments)
        if dist_batiment is not None:
            score_batiment = 15 * max(0.0, 1 - dist_batiment / 150)
            if dist_batiment <= 60:
                raisons.append(f"Proche des bâtiments existants ({dist_batiment:.0f} m) — réseaux à proximité.")
        else:
            score_batiment = 5.0

        score_conflits = 10 * (1 - min(1.0, taux_conflit))
        if taux_conflit <= 0.05:
            raisons.append("Aucun conflit spatial détecté dans la zone.")

        sup_constructible = (espace.superficie or 0) * (espace.taux_occupation / 100)
        sup_deja_allouee = calculer_superficie_allouee_espace(espace)
        projected = sup_deja_allouee + superficie_requise
        if sup_constructible > 0:
            if projected <= sup_constructible:
                score_urbanisme = 10.0
                raisons.append(f"Respecte le taux d'occupation réglementaire ({espace.taux_occupation:.0f}%).")
            else:
                depassement = (projected - sup_constructible) / sup_constructible
                score_urbanisme = max(0.0, 10 * (1 - depassement))
                contraintes.append(
                    f"Dépasse la capacité constructible réglementaire de l'espace "
                    f"({espace.taux_occupation:.0f}% max)."
                )
        else:
            score_urbanisme = 0.0

        score = max(0.0, min(100.0, round(
            score_superficie + score_voirie + score_acces + score_batiment
            + score_conflits + score_urbanisme, 1
        )))

        if not compatible:
            niveau = 'incompatible'
        elif score >= 70:
            niveau = 'favorable'
        elif score >= 40:
            niveau = 'moyen'
        else:
            niveau = 'defavorable'

        resultats.append({
            'espace_id': espace.pk,
            'nom': espace.nom,
            'code': espace.code,
            'compatible': compatible,
            'score': score if compatible else 0.0,
            'niveau': niveau,
            'superficie_disponible': round(superficie_disponible),
            'superficie_disponible_ha': round(superficie_disponible / 10000, 2),
            'raisons': raisons,
            'contraintes': contraintes,
            'geojson': json.loads(espace.geometrie.geojson),
            'distance_voirie_m': round(dist_voirie) if dist_voirie is not None else None,
            'distance_batiment_m': round(dist_batiment) if dist_batiment is not None else None,
        })

    resultats.sort(key=lambda r: (not r['compatible'], -r['score']))
    return resultats


# Alias rétrocompatible
recommander_emplacements = recommander_emplacements_implantation


def mettre_a_jour_statut_construction(projet, nouveau_statut):
    """
    Met à jour le statut d'un projet et déclenche le rejet des concurrents
    si passage vers un statut engagé.
    """
    from urbanisme.models import NouvelleConstruction

    ancien_statut = projet.statut
    projet.statut = nouveau_statut
    projet.save(update_fields=['statut'])

    auto_rejetees = []
    if (nouveau_statut in NouvelleConstruction.STATUTS_ENGAGES
            and ancien_statut not in NouvelleConstruction.STATUTS_ENGAGES):
        auto_rejetees = rejeter_projets_concurrents(projet)

    return projet, auto_rejetees
