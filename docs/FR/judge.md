# Évaluation des Réponses (LLM Judge)

L'évaluation automatisée, ou **LLM Judge**, est une étape d'analyse et d'observabilité cruciale dans notre pipeline RAG. Son objectif est de mesurer de manière autonome la qualité, la fiabilité et la pertinence des réponses générées par notre système (LoreKeeper) en se basant sur le contexte documentaire remonté, sans aucune intervention humaine.

## 1. Pourquoi est-ce Important ?

1.  **Prévention des Hallucinations (Faithfulness)** : S'assurer que le modèle ne génère pas d'informations inventées ou contredisant le lore strict de *Aethelgard Online*. Chaque affirmation de la réponse doit être sourcée.
2.  **Validation de la Pertinence** : Mesurer si le contexte remonté par notre recherche hybride (RRF) est réellement utile à la question posée, et si la réponse finale adresse correctement le besoin de l'utilisateur.
3.  **Observabilité et Amélioration Continue** : Garder une trace chiffrée de la qualité des interactions dans notre base de données. Cela nous permet d'identifier les requêtes problématiques, de détecter les faiblesses du RAG et d'affiner nos stratégies d'ingestion ou de prompt à grande échelle.

## 2. Comment ça Fonctionne ?

Notre script `judge.py` intervient via la fonction `_run_judge_sync` en arrière-plan, juste après que la réponse a été streamée à l'utilisateur. Le processus se déroule en trois temps : **préparation**, **évaluation**, et **log**.

### Étape 1 : Préparation du Contexte et du Prompt

Le système compile la question originale (anonymisée), la réponse générée par l'agent, et la liste des extraits de documents utilisés (le `cot_storage` issu de la recherche vectorielle et pleine page). 
Un prompt d'évaluation strict est alors formaté et envoyé à un modèle LLM distinct faisant office de "Juge" (par défaut `llama-3.3-70b-versatile` via Groq, configuré avec une température de `0.0` pour maximiser l'objectivité et le déterminisme).

### Étape 2 : Évaluation et Validation JSON

Le modèle Juge analyse les données fournies et doit obligatoirement répondre sous la forme d'un objet JSON contenant quatre métriques clés évaluées sur une échelle de 1 à 5 :

-   `context_relevance` : Le contexte fourni par la recherche contient-il l'information nécessaire ?
-   `faithfulness` : La réponse finale est-elle parfaitement fidèle au contexte (zéro hallucination) ?
-   `answer_relevance` : La réponse répond-elle directement à la question de l'utilisateur ?
-   `context_coverage` : La réponse exploite-t-elle correctement les informations pertinentes du contexte ?

Le script nettoie ensuite la sortie du LLM (retrait des éventuelles balises Markdown ` json `) et valide rigoureusement la présence et le type de ces clés pour éviter les erreurs de parsing.

### Étape 3 : Traçabilité (`log_to_db_sync`)

Si l'évaluation est valide, les scores sont enregistrés de manière persistante dans notre base de données de logs (Supabase) sous la catégorie `LLM_JUDGE`. Ces métadonnées sont liées au `session_id` et au `user_id`, permettant de croiser ces notes automatiques avec les feedbacks manuels des utilisateurs.

## 3. Avantages de notre Approche

-   **Asynchrone et Non-Bloquant** : Le Juge s'exécute en tant que tâche de fond (`asyncio.create_task` avec un timeout de 20 secondes). L'utilisateur n'attend jamais la fin de cette évaluation pour recevoir sa réponse.
-   **Fail-Safe (Résilience)** : Conformément aux exigences de robustesse du projet, l'ensemble du processus est encapsulé dans un bloc `try/except`. Si le Juge échoue (timeout, modèle indisponible, JSON mal formé), l'erreur est logguée silencieusement sans jamais faire crasher le backend FastAPI.
-   **Agnostique et Modulaire** : L'architecture nous permet de facilement changer le "fournisseur" ou le "modèle" du Juge via le fichier de configuration (par exemple, utiliser un modèle plus lourd spécifiquement pour l'évaluation, indépendamment du modèle de conversation).

En intégrant ce LLM Judge, nous transformons une boîte noire générative en un système mesurable et traçable, répondant ainsi aux standards d'ingénierie et de sécurité requis pour la production.