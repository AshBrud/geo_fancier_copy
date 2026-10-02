---
trigger: model_decision
description: Gouvernance institutionnelle des utilisateurs, modèle hiérarchique à 3 niveaux (Superuser, Admin, Standard), inscription fermée et délégation descendante des permissions.
---

# Règle d'Agent — Gouvernance des Comptes & Modèle RBAC Institutionnel

> **Directive Fondamentale de Sécurité & d'Architecture**  
> Ce document formalise le modèle d'utilisateurs et d'habilitations de **GéoFoncier**. Il s'applique à tout agent IA et à tout contributeur développant sur les modules d'authentification, d'administration et de contrôle d'accès.

---

## 🏛️ 1. Contexte Institutionnel & Inscription Fermée

1. **Vocation administrative exclusive :**
   - GéoFoncier est un progiciel de gouvernance territoriale et de gestion foncière destiné à des institutions publiques (Directions du Cadastre, Ministères, Rectorats universitaires, Collectivités territoriales).
   - La plateforme **n'est pas une application grand public**.
2. **Interdiction de l'auto-inscription (Zero Self-Registration) :**
   - Aucune création de compte publique ou anonyme n'est autorisée sur les interfaces web.
   - Les routes et vues d'inscription libre (`register`) sont désactivées. Le formulaire de connexion (`login`) ne doit comporter aucun lien d'auto-création.
3. **Amorçage souverain via CLI :**
   - L'initialisation du premier compte de la plateforme s'effectue exclusivement en ligne de commande via l'outil d'administration Django :
     ```bash
     python app/manage.py createsuperuser
     ```

---

## 👥 2. La Hiérarchie des Comptes à 3 Niveaux

Le système d'utilisateurs repose sur une structure pyramidale stricte :

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        NIVEAU 1 : SUPERUSER                            │
│   • Unique maître d'instance (Platform Owner / Ministère / DSI)        │
│   • Créé uniquement via CLI (manage.py createsuperuser)                │
│   • Pouvoir absolu sur les politiques globales et les types de compte  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ crée et supervise
┌───────────────────────────────────▼────────────────────────────────────┐
│                         NIVEAU 2 : ADMINS                              │
│   • Administrateurs délégués (Chefs de service, Directeurs, Maires)    │
│   • Créés et habilités exclusivement par le Superuser                  │
│   • Droits de gestion limités au périmètre accordé par le Superuser    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ créent et supervisent
┌───────────────────────────────────▼────────────────────────────────────┐
│                        NIVEAU 3 : STANDARD                             │
│   • Opérateurs, techniciens SIG, géomètres, télépilotes, instructeurs  │
│   • Créés par le Superuser ou par les Admins (si autorisés)            │
│   • Moindre privilège : accès strictement limité aux tâches affectées  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🔐 3. Matrice de Délégation Descendante des Permissions

1. **Règles pour le Superuser :**
   - Il est le **seul détenteur du pouvoir de définir et modifier les permissions disponibles** pour chaque rôle ou groupe de l'application.
   - Il fixe l'enveloppe d'action maximale de chaque compte **Admin** (ex. droit de créer des comptes, droit d'accès aux exports, droit de modification cadastrale).
2. **Règles pour les Admins :**
   - Un Admin ne peut **jamais** modifier ses propres permissions ni celles d'un autre Admin.
   - Un Admin ne peut agir **que sur les comptes Standard**, et ce, **uniquement dans la limite stricte des droits que le Superuser lui a concédés**.
   - *Exemple de gouvernance* : Si le Superuser retire à un profil Admin la permission de créer des comptes, aucun Admin de ce groupe ne peut ajouter de compte Standard.
3. **Règles pour les comptes Standard (Moindre Privilège) :**
   - Les comptes Standard n'héritent d'aucun droit d'administration système ni d'accès à l'annuaire des utilisateurs.
   - Ils n'accèdent qu'aux données, formulaires et territoires qui leur sont nominativement ou fonctionnellement assignés.

---

## 🛡️ 4. Invariants Techniques & Directives de Développement

Pour toute modification liée aux comptes, à l'authentification et aux permissions :

1. **Prévention de l'escalade de privilèges (Anti-Privilege Escalation) :**
   - Aucun formulaire d'édition utilisateur manipulé par un Admin ne doit permettre d'élever un compte au rang d'`Admin` ou de `Superuser`.
   - Seul un Superuser peut promouvoir un compte au rôle d'Admin.
2. **Protection contre l'auto-suppression et l'éviction :**
   - Il est impossible pour un Admin de supprimer ou désactiver un compte Superuser ou un compte Admin homologue.
   - La désactivation logique (`is_active = False`) doit être privilégiée par rapport à la suppression physique en base afin de préserver l'audit trail (`ActivityLog`).
3. **Indépendance vis-à-vis des spécificités locales :**
   - Les formulaires d'administration des utilisateurs ne doivent plus exiger de champ spécifique à un territoire (comme le village de Ngogom ou le format téléphonique unique +221) : l'attribution territoriale se fait par rattachement explicite et non par couplage dur.
4. **Vérification systématique des habilitations :**
   - Toute vue de gestion doit tester l'habilitation descendante :
     - Vue Superuser : `request.user.is_superuser`
     - Vue Admin : vérification du droit délégué actif (`can_manage_users`) octroyé par le Superuser.
