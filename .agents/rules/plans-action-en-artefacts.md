---
trigger: model_decision
description: Obligation stricte de consigner tous les plans d'action, feuilles de route, spécifications et analyses détaillées sous forme d'artefacts markdown plutôt que dans le fil de discussion du chat.
---

# Règle d'Agent — Rédaction des Plans d'Action en Artefacts

> **Directive Fondamentale de Communication & de Structuration Opérationnelle**  
> Ce document impose que tout plan d'action, proposition architecturale, feuille de route, rapport d'audit ou cadrage technique soit **systématiquement consigné sous forme d'artefact Markdown persistant** et non déversé dans le fil de discussion du chat.

---

## 🎯 1. La Règle d'Or : L'Artefact pour la Structuration, le Chat pour la Décision

Pour maintenir un espace de travail lisible, traçable et efficace, une séparation stricte est établie entre le **document de travail** (l'artefact) et la **conversation** (le chat feed) :

```text
┌────────────────────────────────────────────────────────┐
│  ARTEFACT MARKDOWN (Document Persistant)               │
│  ➜ Emplacement : <artifactDir>/plan_<domaine>.md       │
│  ➜ Contient : Diagnostic, étapes, matrice, DoD,mermaid │
│  ➜ Validable par l'utilisateur via le bouton « Proceed »│
└───────────────────────────┬────────────────────────────┘
                            │ POINTE VERS
                            ▼
┌────────────────────────────────────────────────────────┐
│  CHAT FEED (Fil de Discussion Concis)                  │
│  ➜ Lien Markdown vers l'artefact                       │
│  ➜ 2 à 3 phrases synthétiques de présentation          │
│  ➜ Question fermée ou demande d'arbitrage              │
│  ➜ ZÉRO paraphrase ou redite du plan                   │
└────────────────────────────────────────────────────────┘
```

---

## 📋 2. Cas d'Usage Nécessitant Obligatoirement un Artefact

L'agent **doit obligatoirement** créer ou mettre à jour un artefact dans les situations suivantes :

1. **Plans d'action et feuilles de route** (ex: `plan_filtrage_rbac_sidebar_v2.md`).
2. **Rapports d'audit et analyses d'écarts** (ex: `rapport_audit_ecarts_rbac.md`).
3. **Cadrages et spécifications d'architecture** (ex: `dossier_workspace_architecture_v2.md`).
4. **Matrices comparatives, tableaux multidimensionnels et diagrammes Mermaid complexes**.
5. **Comptes-rendus de suivi et trackers de projet** (ex: `suivi_avancement_implementation_v2.md`).

---

## 🛠️ 3. Protocole Technique de Création d'un Artefact

Lorsqu'un plan d'action est formalisé, l'agent utilise l'outil `write_to_file` en renseignant scrupuleusement les métadonnées :

```json
{
  "TargetFile": "<appDataDir>\\brain\\<conversation-id>\\plan_<sujet>.md",
  "Overwrite": true,
  "ArtifactMetadata": {
    "Summary": "Résumé concis et précis du plan d'action pour la fonctionnalité X...",
    "UserFacing": true,
    "RequestFeedback": true
  }
}
```

> [!IMPORTANT]
> `RequestFeedback: true` doit être systématiquement positionné sur les plans d'action exécutables afin d'offrir à l'utilisateur le bouton interactif **« Proceed »** pour valider et déclencher la réalisation.

---

## 📐 4. Structure Type d'un Artefact de Plan d'Action

Tout artefact de plan d'action doit adopter le squelette standard suivant :

1. **En-tête & Documents de référence** : Liens vers les règles d'architecture et les trackers existants.
2. **Diagnostic de l'existant & Justification** : Pourquoi ce plan est requis et quelles sont les limites constatées.
3. **Matrice ou Schéma cible** : Visualisation du fonctionnement attendu (diagramme Mermaid, table de correspondance).
4. **Découpage séquentiel par étapes (Phases 1, 2, 3...)** :
   - Fichiers cibles impactés (chemins cliquables `file:///...`).
   - Actions techniques précises à réaliser.
5. **Critères d'acceptation & Définition de Terminé (DoD)** : Tableau des tests de validation et comportements attendus.
6. **Prochaines étapes immédiates** : Actions en attente de la validation utilisateur.

---

## 🚫 5. Pratiques Strictement Proscrites

- ❌ **Interdit** : Déverser un long plan de 50 à 100 lignes directement dans le message du chat.
- ❌ **Interdit** : Résumer ou recopier l'intégralité du plan dans la réponse du chat après avoir créé l'artefact.
- ❌ **Interdit** : Commencer à implémenter du code lorsqu'un plan a été demandé avant que l'utilisateur n'ait validé explicitement l'artefact.
