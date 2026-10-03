---
trigger: model_decision
description: Présence et standard d'usage d'Alpine.js pour la réactivité frontend légère, modales dynamiques, formulaires réactifs et interdiction du Vanilla JS impératif pour la gestion d'état.
---

# Règle d'Agent — Présence & Standard d'Usage d'Alpine.js

> **Standard d'Ingénierie Frontend pour GéoFoncier**  
> Ce document acte la présence d'**Alpine.js** comme bibliothèque déclarative officielle pour toute la réactivité dynamique de surface dans les templates Django (modales, formulaires multi-états, filtres interactifs, accordéons, switchs conditionnels).

---

## 🎯 1. Statut & Rôle d'Alpine.js dans GéoFoncier

Pour concilier la simplicité de l'architecture Django Server-Side Rendering (SSR) et le besoin d'une expérience utilisateur moderne et fluide, GéoFoncier adopte **Alpine.js** :

1. **Chargement global unique** :
   - Alpine.js est importé avec `defer` dans le `<head>` de [`app/templates/base.html`](file:///f:/Coding/partenariat/ngom-ngom/geo_fancier_copy/app/templates/base.html) :
     ```html
     <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js"></script>
     ```
   - Il est disponible sur l'ensemble des pages authentifiées de la plateforme.

2. **Équilibre architectural (Ni SPA lourde, ni Vanilla JS spaghetti)** :
   - **Évite le piège de la SPA** : Pas de pipeline lourd Node.js / Vite / React à maintenir, pas de double routage, pas de réécriture d'API REST pour des besoins de simple UI.
   - **Évite le piège du DOM impératif** : Fini les `document.getElementById()`, `querySelectorAll()`, `classList.toggle()` et listeners imbriqués qui se désynchronisent au moindre re-render.

---

## 🛠️ 2. Quand Utiliser Alpine.js ?

| Cas d'Usage | Recommandation | Directive Technique |
| :--- | :---: | :--- |
| **Modales multi-états & matrices** (ex: Matrice RBAC) |  **Obligatoire** | Gérer l'état complet dans un objet `x-data="monComposant()"`. |
| **Recherche et filtrage local instantané** |  **Obligatoire** | `x-model="searchQuery"`, `x-show="matchesSearch(...)"`. |
| **Champs dépendants / conditionnels** |  **Obligatoire** | `:disabled="isLocked"`, `:checked="isGranted"`, `:class="{ 'active': isActive }"`. |
| **Panneaux dépliants / Toggles UI** |  **Recommandé** | `x-data="{ open: false }"` avec `@click="open = !open"` et `x-show="open"`. |
| **Navigation & Pages standard Django** |  **Ne pas forcer** | Conserver les templates Django standards et les inclusions statiques. |

---

## 📐 3. Modèle d'Implémentation Standard (Pattern de Référence)

### A. Structure du Template HTML
Le composant s'initialise au niveau du conteneur (ex: `<form>` ou `<div>`) :

```html
<form action="{% url 'accounts:mon_action' %}" method="POST" x-data="monComposantManager()">
  {% csrf_token %}
  
  <!-- Champ synchronisé avec l'état Alpine -->
  <input type="hidden" name="target_item" :value="currentItem">

  <!-- Sélecteur déclaratif -->
  <div class="card-item" :class="{ 'active': currentItem === 'opt_1' }" @click="selectItem('opt_1')">
    Option 1
  </div>

  <!-- Switch réactif -->
  <input type="checkbox" name="permissions" value="code_1"
         :checked="isGranted('code_1')"
         :disabled="isLocked('code_1')"
         @change="toggleItem('code_1')">

  <!-- Notice conditionnelle -->
  <div class="notice-danger" x-show="isLocked('code_1')">
    <span x-text="getLockReason('code_1')"></span>
  </div>
</form>
```

### B. Injection Sécurisée des Données Django vers Alpine
Les données complexes calculées par Django sont transmises au composant via des balises JSON sécurisées :

```html
<!-- Sérialisation sûre dans le template -->
<script type="application/json" id="mesDonneesJson">{{ donnees_json|default:"{}"|safe }}</script>

<script>
  function monComposantManager() {
    // Lecture unique et sûre au démarrage
    const rawData = JSON.parse(document.getElementById('mesDonneesJson')?.textContent || '{}');

    return {
      currentItem: 'opt_1',
      data: rawData,

      init() {
        // Initialisation si nécessaire
      },

      selectItem(key) {
        this.currentItem = key;
      },

      isGranted(code) {
        return (this.data[this.currentItem] || []).includes(code);
      }
    };
  }

  // Compatibilité universelle Alpine
  window.monComposantManager = monComposantManager;
  document.addEventListener('alpine:init', () => {
    Alpine.data('monComposantManager', monComposantManager);
  });
</script>
```

---

## 🔒 4. Règles Inviolables de Confidentialité & Sécurité

1. **Zéro `console.log` / `console.warn` en production** :
   - Les permissions, rôles, identifiants, tokens CSRF ou données territoriales ne doivent **jamais** être logués dans la console du navigateur.
2. **Double validation étanche Backend / Frontend** :
   - Alpine.js assure l'expérience utilisateur et l'ergonomie visuelle (`:disabled`, `:checked`).
   - Le backend Django (décorateurs `@require_permission`, vérifications dans les services et vues) assure la **sécurité absolue** et rejette toute requête non autorisée avec un 403.
3. **Compatibilité standard avec le POST Django** :
   - Les formulaires gérés par Alpine doivent conserver leurs attributs HTML natifs (`name="..."`, `value="..."`) afin que `request.POST` côté Django continue de fonctionner sans rupture ni dépendance AJAX obligatoire.

---

## 🚫 5. Pratiques Strictement Proscrites

- ❌ **Interdit** : Manipuler le DOM à la main (`document.getElementById()`, `addEventListener('click')`, `innerHTML = ...`) lorsqu'un composant Alpine est déjà en place.
- ❌ **Interdit** : Réécrire une page complète en React/Vue ou introduire un outil de bundler externe sans validation d'architecture préalable.
- ❌ **Interdit** : Insérer des styles CSS inline dans les attributs Alpine (utiliser exclusivement les classes CSS préexistantes du design system, ex: `accounts.css`, `geofoncier.css`).
