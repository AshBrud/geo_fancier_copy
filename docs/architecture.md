# Architecture

## 1. Vue d'ensemble

```text
                 ┌────────────────────────── Navigateur (PC / téléphone) ──────────────────────────┐
                 │  Templates Django + Bootstrap 5 + Leaflet  (static/js/uad_sig.js)                │
                 └───────────────┬──────────────────────────────────────┬───────────────────────────┘
                                 │ HTML                                  │ GeoJSON (/api/…)
┌────────────────────────────────▼──────────────────────────────────────▼───────────────────────────┐
│ Django 5.2 + GeoDjango + DRF / rest_framework_gis                                                  │
│                                                                                                   │
│  Territoire « site »          Territoire « commune »        Transverses                           │
│  ┌──────────┐ ┌────────────┐  ┌──────────┐                  ┌────────┐ ┌──────────┐ ┌───────────┐  │
│  │ foncier  │ │constructions│ │ commune  │                  │ drones │ │ accounts │ │ dashboard │  │
│  └──────────┘ └────────────┘  └──────────┘                  └────────┘ └──────────┘ └───────────┘  │
│  ┌──────┐ ┌────────────┐                                                                          │
│  │ pdu  │ │ navigation │                                                                          │
│  └──────┘ └────────────┘                                                                          │
└──────────────┬───────────────────────────────────────────┬────────────────────────────────────────┘
               │                                           │
      PostgreSQL + PostGIS                     media/ (photos, GeoTIFF, tuiles XYZ)
                                                           ▲
                                      WebODM (externe) ────┘ photogrammétrie
```

## 2. Applications

| App | URL | Responsabilité | Modèles |
|---|---|---|---|
| `accounts` | `/accounts/` | Authentification, inscription, profils, rôles, journal | `CustomUser`, `ActivityLog` |
| `foncier` | `/foncier/`, `/api/` | Inventaire foncier du site, carte principale, API GeoJSON, imports SIG | `Campus`, `Espace`, `FonctionBatiment`, `Batiment`, `Terrain`, `EspaceVert`, `Voirie`, `PointInteret`, `SuiviTravaux` |
| `constructions` | `/constructions/` | Demandes d'implantation et aide à la décision | `NouvelleConstruction`, `HistoriqueConstruction` |
| `drones` | `/drones/` | Production cartographique par drone, flux vidéo | `Mission`, `PhotoDrone`, `Orthophoto`, `FluxVideo` |
| `commune` | `/commune/` | SIG communal, signalements citoyens | `Commune`, `Village`, `Maison`, `Piste`, `OrthophotoCommune`, `Signalement`, `HistoriqueSignalement`, `Notification` |
| `pdu` | `/pdu/` | Statistiques du plan directeur d'urbanisme | — |
| `navigation` | `/navigation/` | Recherche d'entités | — |
| `dashboard` | `/dashboard/` | Tableaux de bord (accueil, université, commune) | — |

## 3. Modèle spatial

### Deux hiérarchies parallèles

```text
Site (campus)                          Commune
─────────────                          ───────
Campus  (limite, MultiPolygon)         Commune  (limite, MultiPolygon)
 ├─ Espace  (libre/occupé/réservé)      └─ Village  (MultiPolygon, code V-001)
 ├─ Batiment ── FonctionBatiment             └─ Maison  (MultiPolygon, code M-0001,
 ├─ Terrain                                          habitée / non habitée)
 ├─ EspaceVert                          Piste    (MultiLineString)
 ├─ Voirie  (MultiLineString)           Signalement (Point) → Village déduit
 └─ PointInteret                        OrthophotoCommune (tuiles XYZ)
```

Les deux hiérarchies suivent le même schéma : **limite → zones → objets**.
Elles sont à la base de la généralisation décrite dans
[territoires.md](territoires.md).

### Règles géométriques communes

| Règle | Où |
|---|---|
| Stockage en **EPSG:4326** | tous les champs `geometrie` / `emprise` |
| Superficie ou longueur recalculée dans `save()` en **UTM 28N (EPSG:32628)** | chaque modèle spatial |
| Inclusion dans le contenant (tolérance 2 %) | `clean()` de `Espace`, `Village`, `Maison` |
| Pas de chevauchement entre entités de même niveau | `clean()` (`_verifier_chevauchement`) |
| Codes lisibles séquentiels | `_code_suivant` (`V-`, `M-`), `numero` des signalements (`NG-00001`) |

Le campus n'est **jamais** compté comme un espace foncier : il sert de
périmètre de référence (`superficie_campus_totale()`).
Taux d'occupation = (bâtiments + terrains sportifs + espaces verts + voiries) / superficie du campus.

## 4. Workflows métier

Chaque workflow correspond à une étape réelle sur le terrain. Les transitions
de statut passent par des méthodes ou des actions explicites.

### 4.1 Production cartographique par drone (`drones`)

```text
Mission (attente) → import photos → traitement WebODM (externe) → (traitement)
  → import orthophoto GeoTIFF → métadonnées extraites par GDAL → (traitée)
  → validation (valide=True, validateur, date) → intégration → (intégrée)
```

- Une orthophoto n'apparaît sur la carte principale que si `valide=True`
  **et** `mission.statut == 'integree'`.
- L'intégration exige un `tiles_url` : sans tuiles, rien ne s'affiche.
- La suppression d'une mission **ne supprime pas** ses photos ni ses
  orthophotos (`SET_NULL`).
- Le flux vidéo en direct (RTSP → HLS/WebRTC via MediaMTX, enregistrement
  FFmpeg) est disponible sur la page `drones:perspectives`.

### 4.2 Orthophoto communale (`commune importer_orthophoto`)

```text
lien public WebODM → téléchargement GeoTIFF → emprise réelle (canal alpha,
une partie de polygone par zone survolée) → gdal2tiles → media/tiles/commune_ortho_<pk>/
```

### 4.3 Demande de construction (`constructions`)

```text
Demande (zone dessinée ou espace choisi, superficie souhaitée)
  → analyser_disponibilite() : superficie libre brute − constructions engagées
                               ± demandes concurrentes
  → faisable ? oui → rapport ; non → zones alternatives classées
  → statut en_cours → approuvée / rejetée
```

- `constructions/recommandation.py` calcule un **score sur 100** pour les
  espaces de type Libre (jamais Occupé ni Réservé).
- `constructions/signals.py` met à jour les espaces quand le statut change.
  C'est le seul module qui fonctionne par signaux.

### 4.4 Signalement citoyen (`commune`)

```text
Citoyen place un point + catégorie → save() déduit le village
  → publier() : historique initial + notification au maire et aux admins
  → changer_statut() : nouveau → pris en charge → en cours → résolu
                       (uniquement vers l'avant ; historique + notification à l'auteur)
```

La cloche de notifications de la barre du haut est alimentée par
`commune.context_processors.notifications`.

## 5. Rôles et permissions

| Rôle (`CustomUser.role`) | Site (campus) | Commune |
|---|---|---|
| `admin` (ou superuser) | tout | tout, y compris l'édition du territoire |
| `domaine_foncier` | gestion foncière | consultation |
| `administration` | gestion foncière, statistiques | consultation |
| `observateur` | statistiques en lecture | — |
| `maire` | — (redirigé vers `/commune/`) | consultation + gestion des signalements |
| `citoyen` | — (redirigé vers `/commune/`) | ses propres signalements uniquement |

- L'inscription publique crée un compte `citoyen`.
- Les vues utilisent les propriétés `can_manage_foncier`, `can_view_stats`,
  `can_view_commune`, `can_edit_commune`, `can_manage_signalements` et les
  décorateurs de `commune/decorators.py`.

## 6. API

DRF avec authentification par session et `IsAuthenticated` par défaut.
Les réponses sont en GeoJSON (`rest_framework_gis`).

| Endpoint | Contenu |
|---|---|
| `/api/espaces/` | Espaces fonciers |
| `/api/batiments/` | Bâtiments |
| `/api/terrains/`, `/api/espaces-verts/`, `/api/voiries/`, `/api/points-interet/` | Couches du site |
| `/api/orthophotos/` | Orthophotos validées et intégrées |
| `/api/stats/` | Statistiques agrégées |
| `/commune/api/villages/<pk>/maisons/` | Maisons d'un village |

## 7. Front-end

- `templates/base.html` : gabarit, menu selon le rôle, notifications.
- `static/js/uad_sig.js` : initialisation Leaflet partagée (centre par défaut
  **codé en dur sur le campus**, voir [territoires.md](territoires.md)).
- `templates/cartographie/map.html` : carte principale du site.
- `templates/commune/carte.html` + `_couches_js.html` : carte communale.
- `templates/dashboard/_styles.html` : styles partagés des tableaux de bord.

## 8. Fichiers et médias

| Dossier | Contenu | Versionné |
|---|---|---|
| `donnees/` | Données sources SIG (GeoJSON modèles, exports Folium) | oui (modèles) |
| `media/orthophotos/`, `media/orthophotos_commune/` | GeoTIFF importés | non |
| `media/tiles/ortho_<pk>/`, `media/tiles/commune_ortho_<pk>/` | Tuiles XYZ | non |
| `media/photos_drone/`, `media/flux_videos/` | Acquisitions drone | non |
| `media/signalements/`, `media/profils/` | Photos utilisateurs | non |
