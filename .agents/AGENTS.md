# Règle d'agent — GéoFoncier NGOGOM_UAD

> À lire par tout agent (IA ou humain) avant de modifier ce dépôt.
> Documentation détaillée : [`docs/README.md`](../docs/README.md).

## 1. Ce qu'est le projet

Une application web **SIG foncier piloté par drone** (Django + PostGIS).
On y gère un territoire à partir d'images aériennes. Le projet est né d'un
mémoire de fin d'études : *« Conception et mise en place d'une application
basée sur les drones pour une gestion durable du domaine foncier de l'UAD »*
(Université Alioune Diop de Bambey, Sénégal).

Deux territoires sont aujourd'hui couverts :

| Territoire | App Django | Hiérarchie spatiale | Usagers |
|---|---|---|---|
| Campus UAD (Bambey) | `foncier` (+ `constructions`, `pdu`, `navigation`) | Campus → Espaces → Bâtiments / Terrains / Espaces verts / Voiries / POI | Domaine foncier, administration, observateurs |
| Commune de Ngogom | `commune` | Commune → Villages → Maisons (+ Pistes, Signalements) | Maire, citoyens |

Ces modules s'appuient sur des modules transverses :

- `drones` : chaîne de production Mission → photos → WebODM → orthophoto → validation → intégration à la carte ;
- `accounts` : utilisateur personnalisé, rôles et journal d'activité ;
- `dashboard` : statistiques.

## 2. Objectif à long terme (boussole de toute décision)

**Pouvoir travailler sur n'importe quel lieu, chaque lieu étant représenté par
un dossier.**

Ajouter un nouveau territoire (une autre université, commune ou zone
agricole) doit revenir à **créer un dossier** qui décrit ce lieu : limites,
couches SIG, orthophotos, paramètres. On ne doit plus avoir à copier une app
Django ni à modifier des constantes dans le code.

Aujourd'hui, ce n'est **pas encore le cas** : le campus et Ngogom sont codés en
dur dans deux apps distinctes. La cible, l'état actuel et le plan de migration
sont décrits dans [`docs/territoires.md`](../docs/territoires.md).

**Conséquence pour chaque modification :**

1. **N'ajoute pas de nouveau couplage à un lieu précis.** Ne code pas en dur de
   nom de lieu, de coordonnées, de zone UTM, de préfixe de code (`NG-`, `V-`…),
   de logo ni de libellé régional dans du code ou un template générique.
   Si une valeur dépend du lieu, elle va dans la configuration du territoire.
   Si cette configuration n'existe pas encore, centralise la valeur dans **une
   seule** constante nommée et signale-la dans `docs/territoires.md`
   (section « Dette de généricité »).
2. **Fais disparaître la dette que tu croises** quand c'est sans risque, et mets à
   jour l'inventaire dans `docs/territoires.md`.
3. **Pas de nouvelle app par lieu.** Une fonctionnalité utile à Ngogom doit être
   pensée pour « une commune » ; une fonctionnalité du campus pour « un site ».

## 3. Invariants techniques à respecter

- **Stockage en EPSG:4326** pour toutes les géométries. **Calculs métriques**
  (surfaces, longueurs) dans une projection UTM, aujourd'hui 32628 (UTM 28N).
  L'UTM 28N ne couvre que les longitudes −18° à −12°. Pour l'est du Sénégal
  (Tambacounda, Kédougou), il faut UTM 29N (32629). La projection métrique est
  donc une **propriété du territoire**, jamais une constante universelle.
- Les **superficies sont calculées dans `save()`** des modèles. Ne les saisis
  jamais à la main et ne les recalcule pas ailleurs.
- **Les transitions de statut passent par une méthode explicite du modèle** :
  `Signalement.changer_statut`, les actions de vue de `Mission`,
  `NouvelleConstruction.analyser_faisabilite`. Ces méthodes écrivent
  l'historique et les notifications. N'affecte jamais `obj.statut = ...`
  directement dans une vue. Exception connue : `constructions/signals.py`
  réagit aux changements de statut de `NouvelleConstruction`. Ne copie pas ce
  modèle ailleurs.
- **Contrôles géométriques** dans `clean()` : une entité doit être incluse dans
  son contenant (tolérance de 2 %) et ne doit pas chevaucher ses voisines du
  même niveau. Reprends ce modèle pour toute nouvelle couche hiérarchique.
- **Droits** : passe par les propriétés de `CustomUser` (`can_manage_foncier`,
  `can_view_commune`, `can_edit_commune`, `can_manage_signalements`…) et les
  décorateurs (`commune/decorators.py`). Ne teste jamais `user.role == '...'`
  dans une vue.
- **Imports SIG** : passe par des commandes `manage.py`, idempotentes (mise à
  jour par `code`) et avec une option `--dry-run`. Voir `docs/import_sig.md`.
- **Orthophotos** : servies en tuiles XYZ locales (`media/tiles/...`) pour rester
  consultables sans WebODM et sur téléphone.
- **Données minimales du module communal** : `Maison` n'a volontairement que
  géométrie, superficie et statut d'occupation (choix fixé par le cahier des
  charges). N'ajoute pas de champ sans demande explicite.

## 4. Conventions

- **Langue** : le métier est en français (modèles, champs, libellés, messages,
  commits). Garde ce vocabulaire : `superficie`, `geometrie`, `statut`.
- **Plateforme de dev** : Windows, venv local, GDAL/GEOS chargés depuis
  `venv/Lib/site-packages/osgeo` (voir `config/settings.py`). Secrets dans `.env`
  (non versionné).
- **Stack** : Python 3.11, Django 5.2 + GeoDjango, DRF + rest_framework_gis,
  PostgreSQL/PostGIS, GDAL/GeoPandas. Côté navigateur : Bootstrap 5, Leaflet
  (+ Leaflet.draw) et Chart.js chargés par CDN. Pour la chaîne drone : WebODM,
  gdal2tiles, FFmpeg et MediaMTX. Détail dans
  [`docs/technologies.md`](../docs/technologies.md).
- **Front** : templates Django, sans framework SPA ni outil de build. Le JS
  partagé est dans `static/js/uad_sig.js`. N'ajoute pas de bibliothèque front
  sans l'inscrire dans `docs/technologies.md`.
- **Migrations** : versionnées. Une migration de données accompagne tout
  changement qui ferait « disparaître » des données existantes de la carte
  (exemple : `drones/0008_rattache_orthophotos_existantes`).
- **Tests** : il n'y en a aucun pour l'instant. Toute logique métier nouvelle
  (calcul de surface, faisabilité, transitions) devrait venir avec un
  `tests.py` dans l'app.
- **Mémoire universitaire** : l'architecture doit rester **explicable**. Chaque
  workflow doit correspondre à une étape réelle (vol, traitement, validation,
  intégration). Préfère une méthode explicite à un signal implicite.

## 5. Avant de terminer une tâche

- [ ] Aucune nouvelle valeur propre à un lieu n'a été codée en dur (sinon elle est inventoriée).
- [ ] Les calculs métriques utilisent la projection du territoire, pas un SRID littéral nouveau.
- [ ] Les droits passent par les propriétés de `CustomUser`.
- [ ] `python manage.py check` et `python manage.py makemigrations --check` passent.
- [ ] La doc concernée dans `docs/` est à jour.
