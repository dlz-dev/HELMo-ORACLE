# Utilité du Vercel AI SDK

Le **Vercel AI SDK** est une bibliothèque open-source conçue pour accélérer le développement d'interfaces de chat basées sur l'IA. Dans notre projet, il joue un rôle crucial côté frontend (Next.js) pour gérer la communication entre l'utilisateur et le backend FastAPI.

## 1. Streaming Simplifié

La fonctionnalité la plus importante que nous utilisons est le **streaming de réponses**. Les modèles de langage (LLM) génèrent des réponses token par token. Sans un outil adapté, le frontend devrait attendre que la réponse complète soit générée avant de l'afficher, ce qui entraîne une latence perceptible et une mauvaise expérience utilisateur.

Le hook `useChat()` du Vercel AI SDK gère cette complexité de manière transparente :

-   Il établit une connexion avec notre API backend (`/api/chat`).
-   Il reçoit le flux de données (Server-Sent Events) envoyé par FastAPI.
-   Il met à jour l'état du chat en temps réel à chaque fois qu'un nouveau token est reçu.

L'utilisateur voit ainsi la réponse apparaître mot par mot, comme sur des plateformes comme ChatGPT, ce qui rend l'application beaucoup plus réactive et "vivante".

## 2. Gestion de l'État du Chat

Le hook `useChat()` fournit un ensemble complet d'états et de méthodes pour gérer une interface de conversation :

-   `messages`: Un tableau contenant l'historique de la conversation (messages de l'utilisateur et de l'assistant).
-   `input` / `handleInputChange`: L'état de l'input de texte et la fonction pour le mettre à jour.
-   `handleSubmit`: La fonction pour envoyer le message de l'utilisateur au backend.
-   `isLoading`: Un booléen qui indique si une réponse est en cours de génération.

Cela nous évite de devoir réécrire toute cette logique de gestion d'état, nous permettant de nous concentrer sur la personnalisation de l'interface utilisateur.

## 3. Agnosticité du Backend

Bien que le SDK soit développé par Vercel, il est entièrement agnostique. Il ne se soucie pas de savoir si le backend est construit avec FastAPI, Express, ou toute autre technologie.

Il standardise simplement le **format du flux de données** attendu. Notre backend FastAPI a été adapté pour produire un flux compatible avec le protocole du Vercel AI SDK, assurant une intégration parfaite.

En résumé, le Vercel AI SDK est un **accélérateur de développement** qui nous fournit les outils nécessaires pour créer une expérience de chat moderne et réactive, sans avoir à réinventer la roue pour la gestion du streaming et de l'état de la conversation.