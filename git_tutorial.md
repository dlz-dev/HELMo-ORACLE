# Tutoriel GIT : Les Branches

## Explication des branches

- **La branche : MAIN**
Contient le code stable, prêt pour la production. On n'y travaille jamais directement.
- **La branche : DEVELOP**
    
    C'est la branche principale de travail. Elle centralise toutes les nouvelles fonctionnalités terminées avant leur mise en production.
    

### Le cycle de vie : `develop` et `main`

On ne pousse pas tout sur `main` uniquement à la fin du projet. `main` représente les versions stables et fonctionnelles ("releases").

- **Pendant le développement :** On fusionne les branches de fonctionnalités (`feature/`) vers `develop`.
- **Jalons (Milestones) :** Dès qu'une version du projet est stable (ex: la v1.0 avec l'indexation RAG fonctionnelle), on fusionne `develop` vers `main`.
- **En résumé :** `develop` est votre zone de construction continue, `main` est votre vitrine de versions finies.

## Le rôle des développeurs

Chaque développeur suit généralement ce cycle :

1. **Partir de `develop`** pour créer une branche **locale** dédiée à une tâche.
2. Travailler, commiter et tester sur cette branche **locale**.
3. Pousser la branche sur le dépôt distant (dans PyCharm, il y a une option pour se faire beaucoup plus visuel que des lignes de commande)
4. Ouvrir une **Pull Request (PR)** ou **Merge Request** pour fusionner son travail vers `develop` après revue par les pairs.

### Différentes branches

- **`feature/`** : Nouvelle fonctionnalité (ex: `feature/rag-pdf-parser`).
- **`bugfix/`** : Correction d'un bug (ex: `bugfix/fix-vector-db-connection`).
- **`hotfix/`** : Correction urgente directement sur `main`.
- **`docs/`** : Modification de la documentation uniquement.

---

## Comment changer de branche (Switch)

La commande moderne est :

```jsx
git switch nom-de-la-branche
```

*Note : Assurez-vous d'avoir commité ou "stashed" (mis de côté) vos modifications en cours avant de changer, sinon Git pourrait bloquer l'opération.*

## La fusion des branches (Merge)

La fusion consiste à intégrer l'historique d'une branche dans une autre.

1. Se placer sur la branche de destination : `git switch develop`
2. Fusionner la branche source : `git merge feature/ma-feature`
Git crée alors un "commit de fusion" (merge commit) qui lie les deux historiques.

## Merge VS Rebase

- **Merge :** Conserve l'historique réel avec toutes les bifurcations. C'est sûr et non destructif. Recommandé pour fusionner vers les branches partagées (`develop` ou `main`).
- **Rebase :** Réécrit l'historique en déplaçant vos commits au sommet de la branche cible. Cela crée une ligne de temps parfaitement droite (plus propre).
    - *Règle d'or :* Ne jamais faire de rebase sur une branche publique/partagée, seulement sur vos branches locales.

## Les conflits de fusion

Un conflit survient quand Git ne sait pas quelle version choisir (ex: deux personnes ont modifié la même ligne de code).
**Procédure de résolution :**

1. Git interrompt la fusion et marque les fichiers en conflit.
2. Ouvrez les fichiers : vous verrez des balises `<<<<<<<`, `=======`, `>>>>>>>`.
3. Choisissez manuellement le code à garder (ou combinez les deux).
4. Enregistrez le fichier, faites un `git add` pour marquer le conflit comme résolu.
5. Terminez avec `git commit`.