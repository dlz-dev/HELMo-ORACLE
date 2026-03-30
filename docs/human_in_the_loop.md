# Human-in-the-Loop (HITL)

Le concept de **Human-in-the-Loop (HITL)** fait référence à l'intégration de l'intervention humaine dans les processus automatisés d'un système d'intelligence artificielle. Dans notre projet, bien que l'agent soit conçu pour être autonome, nous avons mis en place plusieurs mécanismes qui permettent une supervision et une correction humaines.

Ces mécanismes sont essentiels pour garantir la qualité, la sécurité et l'amélioration continue de notre application.

## 1. Validation des Sources (Guardian)

Le premier point d'intervention humaine se situe au tout début du pipeline d'ingestion de données.

-   **Le Processus Automatisé** : Le composant **Guardian** utilise un LLM pour valider si un document est pertinent pour la base de connaissances.
-   **L'Intervention Humaine** : Si le Guardian rejette un fichier, il n'est pas supprimé. Il est déplacé dans un répertoire de **quarantaine** (`data/quarantine/`).
-   **Le Rôle de l'Humain** : Un administrateur peut (et doit) régulièrement examiner les fichiers en quarantaine.
    -   Si le rejet était une erreur (un **faux négatif**), l'administrateur peut manuellement déplacer le fichier dans le dossier d'ingestion pour qu'il soit traité.
    -   Si le rejet était correct, l'administrateur peut supprimer définitivement le fichier ou l'archiver ailleurs.

Ce processus HITL empêche le système de rejeter à tort des informations précieuses à cause d'une mauvaise interprétation du LLM.

## 2. Supervision des Conversations

Bien que nous n'ayons pas encore d'interface dédiée à l'annotation en temps réel, la journalisation des conversations est une forme passive de HITL.

-   **Le Processus Automatisé** : L'agent discute avec l'utilisateur, recherche des informations et génère des réponses. Chaque interaction est enregistrée.
-   **Le Rôle de l'Humain** : Les développeurs ou les administrateurs peuvent analyser les logs des conversations pour :
    -   **Identifier les "hallucinations"** : Repérer les cas où le LLM a inventé des informations.
    -   **Analyser les échecs de recherche** : Comprendre pourquoi l'agent n'a pas trouvé la bonne information dans la base de connaissances.
    -   **Repérer les sujets non couverts** : Identifier les questions récurrentes des utilisateurs pour lesquelles aucune information n'existe, signalant ainsi un besoin d'ajouter de nouvelles sources de données.

## 3. Amélioration Continue de la Base de Connaissances

L'analyse des conversations (point 2) mène directement à une boucle d'amélioration active.

-   **Le Processus Automatisé** : L'agent répond du mieux qu'il peut avec les informations dont il dispose.
-   **L'Intervention Humaine** : Sur la base de l'analyse des conversations, une équipe humaine peut :
    -   **Corriger les sources existantes** : Si une information dans un document est erronée ou obsolète, elle peut être corrigée et le document ré-ingéré.
    -   **Ajouter de nouvelles sources** : Si un manque d'information est identifié, de nouveaux documents peuvent être rédigés ou trouvés et ajoutés au pipeline d'ingestion.
    -   **Ajuster le prompt système** : Si l'agent se comporte mal de manière répétée, son prompt système peut être modifié pour corriger son comportement.

## Conclusion

Le Human-in-the-Loop n'est pas une faiblesse, mais une **caractéristique essentielle** des systèmes d'IA robustes. Il transforme notre application d'un simple automate en un **système d'apprentissage dynamique**, où l'intelligence humaine et l'intelligence artificielle collaborent pour devenir plus précises et plus utiles au fil du temps.