---
trigger: model_decision
description: Directives d'ingénierie et de standardisation de la suite de tests (pytest-django, conftest, coverage, scripts/) et optimisations de performance pour les projets Django. À consulter lors de la configuration ou de la rédaction des tests d'un projet Django.
---

# 🧪 Règle Générale : Standardisation des Tests & Qualification sous Django (`pytest-django`)

> [!IMPORTANT]
> **Règle d'Ingénierie & Qualité Logicielle** : Tous les projets Django de l'écosystème doivent adopter une suite de tests standardisée reposant sur **`pytest-django`**, **`model-bakery`**, une isolation stricte des configurations de test, et des scripts d'exécution automatisés dans `scripts/`.

---

## 🏛️ 1. Stack Officielle de Test

Pour éliminer la lourdeur du runner natif `manage.py test` et bénéficier d'une vitesse d'exécution maximale :

| Outil | Rôle & Usage |
| :--- | :--- |
| **`pytest`** | Moteur de test principal, runner et framework d'assertions. |
| **`pytest-django`** | Intégration native Django (fixtures `db`, `client`, transaction management). |
| **`pytest-cov`** | Mesure et rapport de couverture de code (seuil minimal : 80%). |
| **`pytest-xdist`** | Parallélisation des tests multi-cœurs (`-n auto`). |
| **`model-bakery`** | Génération déclarative et ultra-rapide d'instances de modèles ORM (`baker.make`). |
| **`pytest-mock`** | Mocking propre via la fixture `mocker`. |
| **`uv`** | Exécution isolée et sans latence (`uv run pytest`). |

---

## ⚙️ 2. Configuration Standardisée (`pyproject.toml`)

Chaque projet Django doit déclarer la configuration suivante dans son `pyproject.toml` :

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
python_files = ["test_*.py", "*_test.py"]
python_functions = ["test_*"]
python_classes = ["Test*"]
testpaths = ["tests", "apps"]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
    "-ra",
    "--reuse-db",
]
markers = [
    "unit: Tests unitaires isolés sans base de données",
    "integration: Tests d'intégration et flux inter-modules",
    "api: Tests d'endpoints API (DRF / Ninja)",
    "slow: Tests volumineux ou lents",
]
filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::PendingDeprecationWarning",
]

[tool.coverage.run]
branch = true
source = ["apps"]
omit = [
    "*/migrations/*",
    "*/tests/*",
    "*/config/*",
    "*/asgi.py",
    "*/wsgi.py",
    "manage.py",
]

[tool.coverage.report]
show_missing = true
skip_covered = true
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]
```

---

## ⚡ 3. Configuration Dédiée aux Tests (`config/settings/test.py`)

Les tests doivent impérativement tourner sur des settings optimisés pour la vitesse :

```python
"""
Configuration dédiée aux tests (hérite de settings.base).
Optimise la vitesse d'exécution en neutralisant les opérations coûteuses.
"""
from .base import *  # noqa: F403

# 1. Hachage ultra-rapide des mots de passe (accélération x20 sur la création d'utilisateurs)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# 2. Base de données de test en mémoire (SQLite) ou PostgreSQL isolé
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# 3. Emails interceptés en mémoire (aucun envoi réel)
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# 4. Cache en mémoire locale
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-test-cache",
    }
}

# 5. Répertoire média éphémère (nettoyé automatiquement)
import tempfile
MEDIA_ROOT = tempfile.mkdtemp()

# 6. Exécution synchrone immédiate des tâches de fond (Celery / Q)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
```

---

## 📂 4. Arborescence des Tests & Fixtures Partagées (`conftest.py`)

L'arborescence doit séparer les tests unitaires purs des tests d'API et d'intégration :

```text
tests/
├── conftest.py          # Fixtures globales réutilisables
├── unit/                # Tests purs sans base de données
│   ├── test_services.py
│   └── test_utils.py
├── integration/         # Tests modèles & signaux (avec DB)
│   └── test_models.py
└── api/                 # Tests endpoints HTTP (DRF / Ninja)
    └── test_views.py
```

### Modèle Officiel de `tests/conftest.py` :

```python
import pytest
from model_bakery import baker
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Client API REST non authentifié."""
    return APIClient()


@pytest.fixture
def user(db):
    """Création d'un utilisateur standard via model-bakery."""
    return baker.make("users.User", email="test@geenkodev.com", is_active=True)


@pytest.fixture
def auth_client(api_client, user):
    """Client API pré-authentifié avec l'utilisateur de test."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_user(db):
    """Création d'un super-administrateur."""
    return baker.make(
        "users.User", email="admin@geenkodev.com", is_staff=True, is_superuser=True
    )
```

---

## 🚀 5. Scripts d'Automatisation des Tests (`scripts/`)

Tout projet doit fournir deux scripts appairés dans `scripts/` pour exécuter les tests localement ou dans les conteneurs Docker :

### 1. `scripts/run-tests.ps1` (Windows)
```powershell
param (
    [string]$Path = "tests/",
    [switch]$Coverage,
    [switch]$FailFast
)

$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$PSScriptRoot\.."

$cmd = "uv run pytest $Path"
if ($FailFast) { $cmd += " -x" }
if ($Coverage) { $cmd += " --cov=apps --cov-report=term-missing --cov-report=html" }

Write-Host "🧪 Running Django tests: $cmd" -ForegroundColor Cyan
Invoke-Expression $cmd
```

### 2. `scripts/run-tests.sh` (Linux / macOS / Docker)
```bash
#!/usr/bin/env bash
set -e

PATH_ARG="${1:-tests/}"
COVERAGE="${2:-false}"

if [ "$COVERAGE" = "true" ]; then
    uv run pytest "$PATH_ARG" --cov=apps --cov-report=term-missing --cov-report=html
else
    uv run pytest "$PATH_ARG" -v
fi
```

---

## 🛡️ 6. Règles d'Or pour la Rédaction des Tests

1. **Isolation de la Base de Données (`@pytest.mark.django_db`)** :
   - Ne décorer avec `@pytest.mark.django_db` **que** les tests qui touchent réellement à l'ORM. Les tests unitaires purs (helpers, validateurs, sérialiseurs) s'exécutent en mémoire sans DB en quelques millisecondes.
2. **Proscription des Requêtes HTTP Réelles** :
   - Tout appel externe (passerelle de paiement, API tierce, webhook) doit être intercepté via `mocker.patch`, `respx` ou `responses`. Aucun test ne doit dépendre du réseau.
3. **Usage de `model-bakery` au lieu de `Model.objects.create`** :
   - Préférer systématiquement `baker.make(MonModele, champ_specifique=valeur)` pour ne définir que les champs pertinents pour le test, tout en satisfaisant automatiquement les clés étrangères (`ForeignKey`) et contraintes non nulles.
4. **Indépendance & Ordre d'Exécution** :
   - Chaque test doit être strictement autonome et reproductible indépendamment de l'ordre d'exécution (pas d'état persistant entre les tests).
