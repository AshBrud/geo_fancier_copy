---
trigger: model_decision
description: Architecture modulaire du projet GéoFoncier, organisation du dossier apps/, symétrie des templates et vues Python, et modularisation des assets statiques CSS/JS
---

# Règle d'Architecture Modulaire — GéoFoncier NGOGOM_UAD

> **À lire impérativement par tout agent (IA ou développeur) avant toute modification de la structure du code.**  
> Cette règle formalise les standards d'organisation résultant de la restructuration modulaire du projet.

---

## 1. Organisation du Répertoire `app/`

Toute la logique métier Django est strictement compartimentée. La racine de `app/` ne doit **jamais** accueillir de nouvelle application en vrac.

```text
app/
├── ⚙️ config/                 # Configuration Django pure (settings, urls, wsgi, asgi)
├── 📦 apps/                   # 🎯 TOUTES LES APPLICATIONS MÉTIER SONT ICI
│   ├── accounts/              # Gestion des comptes, utilisateurs et RBAC
│   ├── commune/               # Cadastre communal de Ngogom (villages, maisons, pistes, signalements)
│   ├── constructions/         # Bâtiments et chantiers du campus UAD
│   ├── dashboard/             # Tableaux de bord et statistiques décisionnelles
│   ├── drones/                # Chaîne WebODM, missions et orthophotos
│   ├── foncier/               # Espaces, parcelles et SIG campus
│   ├── navigation/            # Guidage et itinéraires piétons/véhicules
│   └── pdu/                   # Plan de Déplacement Universitaire
├── 🎨 templates/              # Templates HTML organisés par domaine
├── 🎨 static/                 # CSS & JS modulaires (points d'entrée : geofoncier.css / geofoncier.js)
├── 📁 media/                  # Fichiers téléversés (orthophotos, avatars, pièces jointes)
├── 💾 donnees/                # Données brutes de référence (GeoJSON, SHP, CSV)
└── 🚀 manage.py               # Exécutable CLI
```

### Invariant technique `sys.path` :
Toutes les applications situées dans `app/apps/` sont résolues nativement grâce à :
```python
# Dans config/settings.py, manage.py, wsgi.py et asgi.py :
sys.path.insert(0, str(BASE_DIR / 'apps'))
```
**Conséquence :** Les applications conservent leurs noms simples (`'accounts'`, `'foncier'`) dans `INSTALLED_APPS` afin de préserver intacte la table d'historique des migrations PostGIS (`django_migrations`).

---

## 2. Symétrie Stricte : Vues Python ↔ Templates HTML

Pour chaque application Django, la logique Python et la structure des templates doivent être en **miroir parfait**. Les fichiers monolithiques de 500+ lignes sont proscrits.

### Exemple de référence : `accounts`

| Domaine Métier | Vues Python (`app/apps/accounts/views/`) | Templates (`app/templates/accounts/`) |
|---|---|---|
| **Authentification** | `views/auth.py` (`login_view`, `register_view`, `logout_view`) | `auth/login.html`, `auth/register.html`, `auth/components/` |
| **Profil personnel** | `views/profile.py` (`profile_view`) | `profile/profile.html` |
| **Gestion RBAC & Audit** | `views/management.py` (`users_list`, CRUD, `activity_log`) | `management/list.html`, `form.html`, `confirm_delete.html`, `activity_log.html` |
| **Réinitialisation mot de passe** | Vues standard Django (`auth_views`) | `password_reset/request.html`, `done.html`, `confirm.html`, `complete.html` |

### Règles pour toute nouvelle vue ou restructuration :
1. **Pas de `views.py` monolithique :** Privilégier un package `views/` contenant des sous-modules thématiques et un `__init__.py` réexportant les fonctions publiques.
2. **Pas de templates à plat :** Ranger chaque template dans son sous-dossier fonctionnel (`auth/`, `management/`, etc.).
3. **Composants réutilisables isolés :** Tout bloc visuel répété (ex: panneau gauche, carrousel, badge) doit être extrait dans un sous-dossier `components/` préfixé par un tiret bas (ex: `_left_panel.html`).

---

## 3. Modularité des Assets Statiques (`geofoncier.css` & `geofoncier.js`)

Il est formellement interdit de réintroduire des méga-fichiers de styles ou de scripts en vrac (anciens `uad_sig.css` et `uad_sig.js`).

### Architecture CSS (`app/static/css/`)
Le fichier maître [geofoncier.css](file:///f:/Coding/partenariat/ngom-ngom/geo_fancier_copy/app/static/css/geofoncier.css) orchestre 6 modules spécialisés via `@import` :
1. `global.css` : variables CSS (thème bleu/vert), reset, typographie, utilitaires globaux.
2. `components.css` : cartes, boutons, pills, badges, spinners, modales.
3. `forms.css` : inputs, select, switch, validation d'erreurs, alignement des champs.
4. `map.css` : carte Leaflet plein écran, panneau latéral repliable, légendes, popups.
5. `auth.css` : cinématique de login/register, animations de défilement (tickers), panneau drone.
6. `drones.css` : cartes de mission, badges de statut, indicateurs de vol.

### Architecture JS (`app/static/js/`)
Le fichier maître [geofoncier.js](file:///f:/Coding/partenariat/ngom-ngom/geo_fancier_copy/app/static/js/geofoncier.js) orchestre les modules par domaine :
1. `global.js` : helpers utilitaires, tooltips Bootstrap, gestion du token CSRF, notifications toast.
2. `map.js` : initialisation de la carte Leaflet, fonds de plan (OpenStreetMap, Satellite Esri), recentrage.
3. `layers.js` : contrôle et chargement des couches GeoJSON (espaces, bâtiments, limites communales).
4. `search.js` : barre de recherche dynamique et filtrage textuel/géographique.
5. `charts.js` : graphiques statistiques (Chart.js) du dashboard et des rapports.

---

## 4. Invariants & Interdictions pour les Agents

1. **Ne jamais modifier `AUTH_USER_MODEL = 'accounts.CustomUser'` :** Le modèle utilisateur reste ancré dans `accounts`.
2. **Ne jamais ajouter une app directement dans `app/` :** Toute nouvelle app doit obligatoirement être créée dans `app/apps/<nom_app>/`.
3. **Préservation du design actuel :** Aucune modification de structure ne doit dégrader ou altérer la cohérence visuelle ni le comportement UX actuel.
4. **Pas de suppression sans confirmation :** En environnement sandbox, vérifier la cohérence des imports avant de déprécier ou supprimer un module.
