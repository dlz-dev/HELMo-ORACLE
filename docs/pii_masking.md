# Anonymisation des Données (PII Masking)

L'anonymisation, ou **PII (Personally Identifiable Information) Masking**, est une étape de sécurité cruciale dans notre pipeline de conversation. Son objectif est de détecter et de masquer les informations personnelles et sensibles avant qu'elles ne soient envoyées à des services tiers, comme les API des fournisseurs de modèles de langage (LLM).

## 1. Pourquoi est-ce Important ?

1.  **Confidentialité et Sécurité** : Les conversations des utilisateurs peuvent contenir des données sensibles (noms, adresses e-mail, numéros de téléphone, clés API, etc.). Envoyer ces informations à des services externes représente un risque de fuite de données et une violation de la vie privée.
2.  **Conformité (RGPD)** : Le masquage des données personnelles est une mesure technique qui aide à se conformer aux réglementations sur la protection des données comme le RGPD.
3.  **Prévention de l'Abus** : Empêcher les modèles de langage de recevoir et potentiellement mémoriser des informations sensibles réduit les risques d'utilisation abusive de ces données.

## 2. Comment ça Fonctionne ?

Notre `PIIManager` intervient juste avant que la question de l'utilisateur (et l'historique de la conversation) ne soit envoyée au LLM pour générer une réponse. Le processus se déroule en deux temps : **masquage** à l'envoi et **démasquage** au retour.

### Étape 1 : Masquage (`mask_text`)

Le texte est analysé par une combinaison de deux techniques :

-   **Reconnaissance d'Entités Nommées (NER) avec spaCy** :
    -   Nous utilisons la bibliothèque `spaCy`, un outil de traitement du langage naturel (NLP) puissant.
    -   Un modèle pré-entraîné analyse le texte pour identifier des entités comme les noms de personnes (`PER`), les organisations (`ORG`), les lieux (`LOC`), etc.

-   **Expressions Régulières (Regex)** :
    -   Pour les motifs spécifiques qui ne sont pas toujours bien capturés par les modèles NER (comme les adresses e-mail, les numéros de téléphone, les adresses IP, les clés API), nous utilisons des expressions régulières très précises.

Chaque information sensible détectée est remplacée par un "masque" descriptif, par exemple :
-   `"Mon nom est Jean Dupont."` → `"Mon nom est [PERSON]."`
-   `"Contactez-moi à john.doe@email.com."` → `"Contactez-moi à [EMAIL_ADDRESS]."`

### Étape 2 : Démasquage (`unmask_text`)

Après que le LLM a généré une réponse en utilisant le texte masqué, il est possible que la réponse contienne elle-même certains des masques. Bien que cela soit rare, le `PIIManager` peut, si nécessaire, tenter de restaurer les informations originales si le contexte le requiert. Cependant, dans la plupart des cas, la réponse est transmise telle quelle, car le masquage a déjà protégé les données.

## 3. Avantages de notre Approche

-   **Hybride** : La combinaison de spaCy (pour la sémantique) et des Regex (pour les motifs) offre une couverture de détection large et précise.
-   **Robuste** : Le système est conçu pour être fail-safe. Il vaut mieux masquer une information par erreur (faux positif) que de laisser passer une donnée sensible (faux négatif).
-   **Local** : L'ensemble du processus de masquage s'exécute localement dans notre backend FastAPI. Aucune donnée n'est envoyée à un service externe avant d'être anonymisée.

En intégrant ce `PIIManager`, nous ajoutons une couche de sécurité essentielle qui renforce la confiance des utilisateurs et la robustesse de notre application.