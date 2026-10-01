# Documentation — GéoFoncier NGOGOM_UAD

Application web de **SIG foncier piloté par drone**. Elle sert aujourd'hui au
campus de l'Université Alioune Diop de Bambey (UAD) et à la commune de Ngogom.
L'objectif est de la rendre utilisable sur **n'importe quel lieu décrit par un
dossier**.

## Parcours de lecture

| Vous êtes… | Lisez dans cet ordre |
|---|---|
| Nouveau développeur | [prise_en_main.md](prise_en_main.md) → [technologies.md](technologies.md) → [architecture.md](architecture.md) → [territoires.md](territoires.md) |
| Agent IA | [../.agents/AGENTS.md](../.agents/AGENTS.md), puis les fichiers ci-dessus selon la tâche |
| Géomaticien / importeur de données | [import_sig.md](import_sig.md) → [territoires.md](territoires.md) |
| Encadrant / lecteur du mémoire | [architecture.md](architecture.md) (sections « Workflows ») |

## Contenu

| Fichier | Sujet |
|---|---|
| [prise_en_main.md](prise_en_main.md) | Installation sous Windows, `.env`, premier lancement, commandes utiles |
| [technologies.md](technologies.md) | Technologies utilisées (back-end, SIG, drone, front-end, outils), rôle de chacune et où elles servent |
| [architecture.md](architecture.md) | Apps Django, modèles, workflows métier, rôles, API, carte |
| [territoires.md](territoires.md) | Vision « un lieu = un dossier » : état actuel, cible, dette à résorber, feuille de route |
| [import_sig.md](import_sig.md) | Pipeline GeoPandas → PostGIS, colonnes attendues, commandes d'import |

## En une phrase par module

- **foncier** : inventaire foncier du campus (espaces, bâtiments, terrains, espaces verts, voiries, points d'intérêt, suivi des travaux) et API GeoJSON.
- **constructions** : demandes de nouvelles constructions, avec analyse automatique de disponibilité et de faisabilité, puis zones alternatives.
- **drones** : production cartographique (Mission → photos → WebODM → orthophoto → validation → intégration) et flux vidéo en direct.
- **commune** : SIG de la commune de Ngogom (villages, maisons, pistes, orthophotos, signalements citoyens et notifications).
- **pdu** : statistiques liées au plan directeur d'urbanisme.
- **navigation** : recherche d'entités sur la carte.
- **dashboard** : tableaux de bord du campus et de la commune.
- **accounts** : utilisateurs, rôles et journal d'activité.

## Maintenir cette documentation

- Une modification qui change un workflow, un rôle ou une convention met à jour le fichier concerné **dans le même commit**.
- Toute valeur propre à un lieu ajoutée au code doit être inscrite dans la section « Dette de généricité » de [territoires.md](territoires.md).
