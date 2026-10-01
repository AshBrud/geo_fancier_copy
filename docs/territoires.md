# Territoires : « un lieu = un dossier »

## 1. L'objectif

> À terme, l'application doit pouvoir travailler sur **n'importe quel lieu**
> (université, commune, zone agricole, quartier…). **Chaque lieu est représenté
> par un dossier.** Ajouter un lieu = déposer un dossier et lancer une
> commande. Aucune modification du code n'est nécessaire.

Deux lieux sont gérés aujourd'hui : le **campus de l'UAD** et la **commune de
Ngogom**. Ils montrent que le modèle fonctionne. Ils montrent aussi le problème :
chaque lieu a été codé « à la main » dans sa propre app Django (`foncier`,
`commune`).

## 2. Ce qui est déjà générique

Ces acquis doivent être conservés et réutilisés :

- **Hiérarchie spatiale identique** : limite → zones → objets
  (Campus → Espaces → Bâtiments ; Commune → Villages → Maisons).
- **Calcul automatique des superficies** et **contrôles d'inclusion et de
  non-chevauchement** (`commune/models.py` : `_superficie_m2`,
  `_verifier_inclusion`, `_verifier_chevauchement`, `_code_suivant`).
- **Chaîne drone** indépendante du lieu (Mission → WebODM → orthophoto → tuiles).
- **Imports SIG par commande**, idempotents par `code`, avec option `--source-crs`
  (`foncier/management/commands/_sig_import.py`).
- **Permissions centralisées** dans `CustomUser`.

## 3. La cible

### 3.1 Arborescence proposée

```text
territoires/
├── _modele/                     ← squelette à copier pour un nouveau lieu
│   ├── territoire.toml
│   └── README.md
├── uad-campus/
│   ├── territoire.toml          ← identité et paramètres du lieu
│   ├── README.md                ← contexte terrain, contacts, historique des vols
│   ├── limite.geojson           ← périmètre (1 polygone ou multipolygone)
│   ├── couches/                 ← une couche = un fichier
│   │   ├── espaces.geojson
│   │   ├── batiments.geojson
│   │   ├── voiries.geojson
│   │   └── ...
│   ├── orthophotos/
│   │   └── sources.toml         ← liens WebODM / chemins GeoTIFF (fichiers lourds hors Git)
│   └── identite/
│       └── logo.svg
└── ngogom/
    ├── territoire.toml
    ├── limite.geojson
    ├── couches/
    │   ├── villages.geojson
    │   ├── maisons.geojson
    │   └── pistes.geojson
    └── orthophotos/sources.toml
```

> Le **slug** du dossier (`uad-campus`, `ngogom`) est l'identifiant stable du
> lieu : il sert dans les URL, les chemins `media/` et les préfixes de code.

### 3.2 Fichier `territoire.toml` (proposition)

TOML est lisible par la bibliothèque standard (`tomllib`, Python ≥ 3.11), donc
sans dépendance supplémentaire.

```toml
slug        = "ngogom"
nom         = "Commune de Ngogom"
type        = "commune"            # "site" (campus, domaine) | "commune" | ...
pays        = "Sénégal"
region      = "Diourbel"
departement = "Bambey"

[carte]
centre      = [14.751, -16.524]    # lat, lon
zoom        = 15
srid_metrique = 32628              # UTM 28N ; 32629 à l'est de −12° de longitude

[codes]
prefixe_signalement = "NG"
zone   = "V-"                      # villages
objet  = "M-"                      # maisons

[hierarchie]                       # libellés affichés à l'écran
limite = "Commune"
zone   = "Village"
objet  = "Maison"

[identite]
logo = "identite/logo.jpg"
titre_application = "GéoFoncier Ngogom"
```

### 3.3 Fonctionnement attendu

```text
manage.py charger_territoire territoires/ngogom [--dry-run]
   1. lit territoire.toml  → crée/maj l'enregistrement Territoire
   2. importe limite.geojson
   3. importe couches/*.geojson via les commandes import_* existantes
   4. importe les orthophotos déclarées
```

Côté application :

- un modèle **`Territoire`** (slug, type, paramètres) ; toutes les entités
  spatiales s'y rattachent (clé étrangère) ;
- le **territoire actif** est choisi par l'URL (`/t/<slug>/…`) ou par la
  session, et il est rattaché à l'utilisateur (un maire n'a accès qu'à sa commune) ;
- la carte, les tableaux de bord et les calculs lisent **centre, zoom, SRID,
  libellés et préfixes** depuis le territoire, et non depuis le code.

## 4. Dette de généricité (inventaire)

Ce sont les valeurs propres à un lieu qui sont aujourd'hui codées en dur. **À
tenir à jour** : chaque ajout ou suppression se reporte ici.

| Valeur | Emplacement(s) | Devient |
|---|---|---|
| SRID métrique `32628` | `foncier/models.py` (6×), `drones/models.py`, `commune/models.py` (`UTM_SRID`), `constructions/recommandation.py` (`UTM_SRID`) | `territoire.srid_metrique` |
| Centre de carte du campus `14.6963, -16.4774` | `static/js/map.js`, `templates/cartographie/map.html`, `foncier/management/commands/export_carte_folium.py` | `territoire.carte.centre` |
| `default='Campus UAD Bambey'` | `foncier/models.py` (`Campus.nom`) | `territoire.nom` |
| `default='Ngogom'`, `'Bambey'`, `'Diourbel'` | `commune/models.py` (`Commune`) | `territoire.toml` |
| Préfixe `NG-` des signalements | `commune/models.py` (`Signalement.numero`) | `codes.prefixe_signalement` |
| Préfixes `V-`, `M-` | `commune/models.py` (`_code_suivant`) | `codes.*` |
| « Université Alioune Diop de Bambey », image `drone_campus.jpg` | `templates/accounts/auth/login.html`, `templates/accounts/password_reset/*.html` | `identite.*` |
| Nom d'application `GéoFoncier NGOGOM_UAD` | `config/settings.py` (`DEFAULT_FROM_EMAIL`), templates | `identite.titre_application` |
| Logos `logo_uad_sig.svg`, `logo_ngogom.jpg` | `static/images/` | `territoires/<slug>/identite/` |
| Hypothèse « un seul Campus / une seule Commune » | `superficie_campus_totale()` (`Campus.objects.first()`), `Commune` | filtrage par territoire actif |
| Rôles `maire`/`citoyen` sans rattachement à une commune | `accounts/models.py` (`village` seulement) | rattachement utilisateur ↔ territoire |
| Libellé d'exemple « Piste Ngogom – Bambey » | `commune/forms.py` | texte neutre |

## 5. Feuille de route proposée

Chaque étape peut être livrée seule et garde l'application fonctionnelle.

| Étape | Contenu | Risque |
|---|---|---|
| **0. Centraliser** | Regrouper les constantes de l'inventaire dans un module unique (ex. `config/territoire.py`) sans changer le comportement | Très faible |
| **1. Dossiers** | Créer `territoires/uad-campus/` et `territoires/ngogom/` avec `territoire.toml` + données sources existantes (`donnees/`) | Nul (pas de code) |
| **2. Modèle `Territoire`** | Nouvelle app légère ; FK nullable sur `Campus` et `Commune` ; migration de données qui crée les deux territoires existants | Faible |
| **3. Commande `charger_territoire`** | Orchestre les commandes `import_*` et `importer_orthophoto` à partir d'un dossier | Faible |
| **4. Territoire actif** | Middleware ou préfixe d'URL ; carte, tableaux de bord et SRID lus depuis le territoire | Moyen |
| **5. Unifier les hiérarchies** | Faire de « site » et « commune » deux *types* de territoire sur un socle commun (limite / zone / objet) plutôt que deux apps | Élevé, à décider |

## 6. Critère de réussite

> Un développeur qui ne connaît pas le projet copie `territoires/_modele/`, le
> remplit pour un nouveau lieu, lance `charger_territoire`, et voit ce lieu sur
> la carte **sans avoir ouvert un seul fichier `.py` ni `.html`**.
