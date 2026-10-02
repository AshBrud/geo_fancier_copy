---
trigger: model_decision
description: Système de permissions granulaires [domaine]:[action], séparation stricte Migrations Django (DDL) vs Seeder Idempotent (DML), défense en profondeur à 3 niveaux et délégation descendante.
---

# Règle d'Agent — Système de Permissions Granulaires (RBAC) & Stratégie de Seeding

> **Norme Fondamentale de Sécurité & d'Orchestration des Données**  
> Ce document formalise l'adaptation pour **Django / GeoDjango** de la stratégie de permissions RBAC et du cycle de seeding idempotent issus des standards GeenkoDev.

---

## 🎯 1. La Règle d'Or : Migrations Django (DDL) vs Seeder Idempotent (DML)

Pour garantir la maintenabilité et la robustesse des déploiements conteneurisés (Coolify / Docker), une frontière étanche sépare la structure de la base de son initialisation :

```text
┌────────────────────────────────────────────────────────┐
│  MIGRATIONS DJANGO (DDL) : STRUCTURE DES TABLES        │
│  ➜ Commande : python app/manage.py migrate             │
│  ➜ Gère tables, colonnes, indexes spatiaux, contraintes│
│  ➜ ZÉRO injection de permissions ou de rôles           │
└───────────────────────────┬────────────────────────────┘
                            │ APRÈS MIGRATIONS
                            ▼
┌────────────────────────────────────────────────────────┐
│  SEEDER IDEMPOTENT (DML) : INJECTION DES PERMISSIONS   │
│  ➜ Commande : python app/manage.py seed_rbac           │
│  ➜ Crée/actualise les permissions atomiques            │
│  ➜ Configure les rôles de base et leurs liaisons       │
│  ➜ Exécuté automatiquement à chaque démarrage          │
└────────────────────────────────────────────────────────┘
```

### 💡 Pourquoi ce choix d'ingénierie est obligatoire :
1. **Évite la prolifération des migrations vides** : L'ajout d'une nouvelle permission (ex: `drones:export`) se fait par déclaration dans le dictionnaire du seeder, sans créer une migration Django de pur contenu.
2. **Synchronisation automatique en déploiement continu** : Dès qu'un nouveau conteneur démarre avec du nouveau code, les nouvelles permissions sont instantanément insérées et synchronisées de manière idempotente sans intervention manuelle.
3. **Zéro conflit en équipe** : Deux développeurs ajoutant des permissions ne génèrent aucun conflit de fusion de migrations Django (`merge migrations`).

---

## ⚙️ 2. Cycle de Démarrage Docker (`docker/entrypoint.sh`)

L'orchestration au démarrage du conteneur doit respecter l'ordre strict suivant :

```bash
# 1. Attente active de la base PostgreSQL / PostGIS
# ...

# 2. Exécution des migrations structurelles (DDL)
echo "🔄 [GéoFoncier] Exécution des migrations PostGIS..."
python app/manage.py migrate --noinput

# 3. Seeding idempotent des permissions et rôles (DML)
echo "🌱 [GéoFoncier] Initialisation / Synchronisation idempotente du RBAC..."
python app/manage.py seed_rbac || true

# 4. Collecte des fichiers statiques (WhiteNoise)
echo "📦 [GéoFoncier] Collecte des fichiers statiques..."
python app/manage.py collectstatic --noinput --clear || true

# 5. Lancement de Gunicorn
exec "$@"
```

---

## 🏷️ 3. Nomenclature Granulaire des Permissions : `[domaine]:[action]`

Chaque permission atomique de GéoFoncier suit la convention universelle :
`[domaine]:[action]` ou `[domaine]:[sous-domaine]:[action]`

### Les Actions Canoniques :
- `:view` ➔ Lecture / consultation de la ressource ou accès à la page/module.
- `:create` ➔ Création d'une nouvelle ressource.
- `:update` ➔ Modification d'une ressource existante.
- `:delete` ➔ Désactivation logique ou suppression d'une ressource.
- `:export` ➔ Exportation de fichiers (GeoJSON, Shapefile, CSV, PDF).
- `:manage` ➔ Pilotage administratif complet du sous-système.

### Matrice par Domaines Métier de GéoFoncier :

| Domaine Métier | Permissions Définies | Description & Périmètre de Protection |
| :--- | :--- | :--- |
| **Cadastre & Foncier** | `cadastre:view`<br>`cadastre:create`<br>`cadastre:update`<br>`cadastre:delete`<br>`cadastre:export` | Consultation, délimitation de parcelles, création de bâtiments, modification d'espaces et export SIG. |
| **Drones & Imagerie** | `drones:view`<br>`drones:upload`<br>`drones:process`<br>`drones:delete` | Consultation des orthophotos, téléversement de missions, lancement de chaîne photogrammétrique. |
| **Aménagement & PDU** | `pdu:view`<br>`pdu:create`<br>`pdu:update`<br>`pdu:simulate` | Plans d'urbanisme, prévisions d'implantations et capacité constructible. |
| **Utilisateurs & Sécurité**| `users:view`<br>`users:create`<br>`users:update`<br>`users:delete`<br>`users:delegate` | Gestion des agents, réinitialisation de mots de passe, attribution de permissions. |
| **Territoires & Dossiers** | `territoires:view`<br>`territoires:create`<br>`territoires:update`<br>`territoires:switch` | Création de dossiers communaux ou universitaires, bascule de contexte. |
| **Configuration Système** | `settings:view`<br>`settings:update` | Paramètres généraux de l'instance et intégrations externes. |

---

## 🛡️ 4. Application de la Sécurité : Défense en Profondeur à 3 Niveaux

La sécurité est appliquée de façon étanche à travers 3 échelons :

```text
┌────────────────────────────────────────────────────────┐
│  NIVEAU 1 : BACKEND DJANGO (Garantie Ultime)           │
│  ➜ Décorateur @require_permission("cadastre:create")   │
│  ➜ Rejette toute requête non autorisée avec un 403     │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│  NIVEAU 2 : MIDDLEWARES & ROUTAGE INTERNE              │
│  ➜ Vérification du statut actif et du rôle d'accès     │
│  ➜ Redirection vers le dashboard si hors périmètre     │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│  NIVEAU 3 : INTERFACE HTML / TEMPLATES DJANGO          │
│  ➜ Tags template : {% if user_can 'cadastre:create' %} │
│  ➜ Masque boutons, formulaires et menus latéraux       │
└────────────────────────────────────────────────────────┘
```

### Niveau 1 : Le Décorateur Backend
```python
# accounts/decorators.py
def require_permission(perm_name: str):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if not request.user.has_perm_name(perm_name):
                raise PermissionDenied(f"Permission manquante : {perm_name}")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

### Niveau 3 : Les Templates Django
```html
<!-- Exemple : Bouton de création masqué si l'opérateur n'a que la lecture -->
<div class="d-flex justify-content-between align-items-center mb-3">
  <h2>Parcelles Cadastrales</h2>
  {% if user_can 'cadastre:create' %}
    <a href="{% url 'foncier:espace_create' %}" class="btn btn-primary">
      <i class="bi bi-plus-lg"></i> Ajouter une parcelle
    </a>
  {% endif %}
</div>
```

---

## 🔁 5. Algorithme de Délégation Descendante & Idempotence

1. **Superuser** : Possède implicitement toutes les permissions (`*:*`).
2. **Admin Délégué** : Se voit attribuer une liste de permissions autorisées $P_{admin}$.
3. **Attribution à un compte Standard** :
   Lorsqu'un Admin configure un compte Standard avec des permissions $P_{standard}$ :
   $$\text{Validation stricte :} \quad P_{standard} \subseteq P_{admin}$$
   Si une permission demandée pour le compte Standard n'est pas détenue par l'Admin, le formulaire rejette la requête côté serveur avec une erreur de validation explicite.
4. **Idempotence du Seeder** :
   - Le seeder vérifie l'existence de chaque permission par son nom unique avant création.
   - Les rôles par défaut sont mis à jour sans écraser les attributions personnalisées créées en production.
