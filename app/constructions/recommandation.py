"""
Système d'aide à la décision pour l'implantation des nouvelles constructions.

Analyse tous les sous-espaces fonciers de type Libre (jamais les espaces
Occupés ou Réservés), vérifie les contraintes réglementaires/spatiales et
calcule un score de pertinence sur 100 pour classer les emplacements du plus
favorable au moins favorable.
"""
import json

from foncier.models import Espace, Batiment, Voirie, Terrain, EspaceVert, Campus

UTM_SRID = 32628


def _to_utm(geom):
    return geom.transform(UTM_SRID, clone=True)


def _nearest_distance_m(point_utm, objets):
    """Plus courte distance (en mètres) entre un point UTM et une liste d'objets géoréférencés."""
    best = None
    for obj in objets:
        if not obj.geometrie:
            continue
        d = point_utm.distance(_to_utm(obj.geometrie))
        if best is None or d < best:
            best = d
    return best


def recommander_emplacements(type_construction, superficie_requise, zone_dessinee=None):
    """
    Retourne une liste de dicts (JSON-sérialisables), un par sous-espace Libre
    analysé, triée du meilleur au moins favorable :
      compatible, score (/100), niveau (favorable|moyen|defavorable|incompatible),
      superficie_disponible, raisons[], contraintes[], geojson.

    Si `zone_dessinee` (GEOSGeometry Polygon) est fournie, seul le ou les
    espaces Libres qui la contiennent entièrement sont évalués sur cette
    géométrie exacte (mode « emplacement précis »). Sinon, chaque espace
    Libre est évalué dans son ensemble (mode « recommandation automatique »).
    """
    from constructions.models import NouvelleConstruction

    superficie_requise = superficie_requise or 0
    campus = Campus.objects.first()
    espaces_libres = Espace.objects.filter(type_espace=Espace.TYPE_LIBRE).order_by('nom')

    batiments        = list(Batiment.objects.all())
    voiries          = list(Voirie.objects.all())
    terrains_sportifs = list(Terrain.objects.filter(type_terrain__icontains='sport'))
    espaces_verts    = list(EspaceVert.objects.all())

    resultats = []

    for espace in espaces_libres:
        if not espace.geometrie:
            continue

        raisons, contraintes = [], []
        compatible = True

        # ── Contrainte : la zone doit appartenir au campus ────────────────
        if campus and campus.geometrie and not campus.geometrie.contains(espace.geometrie):
            contraintes.append("Hors du périmètre du Campus.")
            compatible = False

        # ── Zone à tester ──────────────────────────────────────────────────
        if zone_dessinee is not None:
            if not espace.geometrie.contains(zone_dessinee):
                continue
            zone_test = zone_dessinee
        else:
            zone_test = espace.geometrie

        zone_test_utm   = _to_utm(zone_test)
        superficie_zone = zone_test_utm.area

        def _intersectants(objets):
            return [o for o in objets if o.geometrie and zone_test.intersects(o.geometrie)]

        bat_conf = _intersectants(batiments)
        voi_conf = _intersectants(voiries)
        ter_conf = _intersectants(terrains_sportifs)
        ev_conf  = _intersectants(espaces_verts)

        if zone_dessinee is not None:
            # Mode précis : toute intersection est disqualifiante.
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
            # Mode automatique : on retranche la surface déjà occupée par les
            # couches en conflit pour obtenir la surface réellement libre.
            occupee_geom = None
            for o in (bat_conf + voi_conf + ter_conf + ev_conf):
                occupee_geom = o.geometrie if occupee_geom is None else occupee_geom.union(o.geometrie)
            try:
                zone_libre = zone_test.difference(occupee_geom) if occupee_geom is not None else zone_test
            except Exception:
                zone_libre = zone_test
            superficie_disponible = _to_utm(zone_libre).area if zone_libre else 0.0
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

        # ── Score multicritère (100 pts) ──────────────────────────────────
        score_superficie = 30 * min(1.0, superficie_disponible / (superficie_requise * 1.5)) \
            if superficie_requise > 0 else 0.0

        centroid_utm = zone_test_utm.centroid
        dist_voirie = _nearest_distance_m(centroid_utm, voiries)
        if dist_voirie is not None:
            score_voirie = 20 * max(0.0, 1 - dist_voirie / 300)
            score_acces  = 15 * max(0.0, 1 - dist_voirie / 600)
            if dist_voirie <= 100:
                raisons.append(f"Très proche d'une voirie ({dist_voirie:.0f} m) — bon accès.")
            elif dist_voirie > 400:
                contraintes.append(f"Éloigné des voiries ({dist_voirie:.0f} m) — accès à prévoir.")
        else:
            score_voirie, score_acces = 8.0, 6.0
            contraintes.append("Aucune voirie référencée à proximité pour évaluer l'accès.")

        dist_batiment = _nearest_distance_m(centroid_utm, batiments)
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
        sup_deja_allouee  = NouvelleConstruction.superficie_allouee_espace(espace)
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
            'espace_id':                espace.pk,
            'nom':                      espace.nom,
            'code':                     espace.code,
            'compatible':               compatible,
            'score':                    score if compatible else 0.0,
            'niveau':                   niveau,
            'superficie_disponible':    round(superficie_disponible),
            'superficie_disponible_ha': round(superficie_disponible / 10000, 2),
            'raisons':                  raisons,
            'contraintes':              contraintes,
            'geojson':                  json.loads(espace.geometrie.geojson),
            'distance_voirie_m':        round(dist_voirie) if dist_voirie is not None else None,
            'distance_batiment_m':      round(dist_batiment) if dist_batiment is not None else None,
        })

    resultats.sort(key=lambda r: (not r['compatible'], -r['score']))
    return resultats
