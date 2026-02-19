# 🗺️ Roadmap : Du Prototype Oracle au Moteur RAG Entreprise

~~## Phase 1 : Ingestion "Context-Aware" (Markdown & Documents)~~

**Le Problème :** Actuellement, le convertisseur Markdown découpe le fichier ligne par ligne ou par bloc isolés. Si l'Oracle trouve une réponse dans une liste à puces, il perd le titre qui expliquait de quoi parlait cette liste.

**La Solution (Inspirée de LangChain & Medium) :**

* **MarkdownHeaderTextSplitter :** Au lieu de découper par taille, on découpe par structure. Le texte est rattaché à ses métadonnées (Headers). Si le bot trouve un paragraphe, il "sait" qu'il appartient au chapitre "Règlement Intérieur" grâce aux métadonnées injectées.
* **Metadata Enrichment :** Chaque vecteur dans Supabase doit contenir le nom du fichier, la page (pour les PDF) et le niveau de titre. Cela permet à l'IA de citer ses sources précisément ("Selon le document RH, page 12...").
  * Chaque "chunk" (morceau de texte) envoyé à Supabase doit être accompagné d'un dictionnaire de métadonnées (titre du document, auteur, date, etc.).

**Sources :** 
- https://medium.com/@vishalkhushlani123/building-a-markdown-knowledge-ingestor-for-rag-with-langchain-ba201515f6c4
- https://medium.com/@msriarunm/document-loaders-feeding-data-into-rag-91e3ff36ff60

---

## Phase 2 : Late Chunking (Le "Copier/Coller" LocalGPT)

**Le Problème :** Dans les textes longs, un "chunk" au milieu du document perd le contexte global. Le vecteur représente le sens du paragraphe, mais oublie qu'il fait partie d'un contrat spécifique signé en 2024.

**La Solution (Implémentation LocalGPT) :**

* **Global Encoding :** On passe le document entier (ou de très grandes sections) dans le modèle d'embedding avant de découper.
* **Contextual Embeddings :** Le vecteur généré pour un paragraphe "hérite" du sens global du document. C'est crucial pour les entreprises traitant des rapports de 50 pages où le sujet n'est rappelé qu'en introduction.

**Sources :** 
- https://jina.ai/news/late-chunking-in-long-context-embedding-models/
- https://github.com/PromtEngineer/localGPT?tab=readme-ov-file (Numéro 2 des tendances GitHub sur un RAG Local)

---

## Phase 3 : Intelligence & Mémoire (Expérience Utilisateur)

**Le Problème :** L'historique Streamlit actuel est volatil et s'efface au rafraîchissement, et l'IA cherche parfois dans les documents pour rien.

**La Solution :**

* **Local Persistent History :** Sauvegarde des échanges dans un dossier `storage/sessions/` sous format JSON. Chaque utilisateur retrouve sa conversation grâce à un ID de session.
* **ConversationSummaryBufferMemory :** Utilisation de LangChain pour résumer les vieux échanges tout en gardant les messages récents intacts, évitant de saturer la fenêtre de contexte.
* **Query Triage :** Ajout d'une étape de décision où l'IA classifie la question : "Recherche RAG requise", "Réponse via historique" ou "Simple politesse".

---

## Phase 4 : Recherche Hybride & Re-ranking

**Le Problème :** La recherche vectorielle (sémantique) est excellente pour le sens, mais médiocre pour les termes techniques exacts ou les codes produits (ex: "Project-X92"). Ton `VectorManager` actuel ne fait que de la distance Euclidienne.

**La Solution (Architecture Pro) :**

* **BM25 + Vector :** On effectue deux recherches en parallèle. Une recherche par mots-clés "classique" (FTS - Full Text Search dans Supabase) et une recherche vectorielle.
* **Reranker :** On prend les 10 meilleurs résultats des deux méthodes et on utilise un modèle de "Re-ranking" (plus petit et rapide que Llama) pour classer ces résultats par pertinence réelle avant de les donner à l'Oracle (via ColBERT).

**Source :**
- https://github.com/PromtEngineer/localGPT?tab=readme-ov-file (Numéro 2 des tendances GitHub sur un RAG Local)

---

## Phase 5 : Fiabilité & Sécurité (Production)

**Le Problème :** Envoyer des données brutes en entreprise pose des risques de fuites de données sensibles et de bugs en production.

**La Solution :**

* **Automated Testing :** Mise en place de tests unitaires (Pytest) pour valider que les convertisseurs (CSV, MD, PDF) ne corrompent pas les données lors de l'ingestion.
* **PII Masking (Anonymisation) :** Filtre de sécurité détectant les noms, emails ou numéros de téléphone pour les masquer avant l'envoi aux APIs cloud (Groq/OpenAI).
* **Local Switch :** Option dans `config.yaml` pour basculer sur un modèle local (Ollama/Llama 3) pour les documents classés confidentiels.

---

## Phase 6 : Interface & Déploiement (Scalabilité)

**Le Problème :** Le projet doit pouvoir être utilisé par n'est pas limité à Streamlit et doit accepter des nouveaux documents facilement.

**La Solution :**

* **Drag & Drop UI :** Intégration d'un module d'upload direct dans Streamlit pour alimenter la base de connaissances sans relancer de scripts manuels.
* **Architecture Multi-plateforme :** Séparation du code en deux parties : un **Backend (FastAPI)** qui gère l'IA et un **Frontend (Streamlit/React)**. Cela permet d'intégrer l'Oracle dans Slack, Teams ou un site web métier.

---

## 🛠️ Zoom technique : Le Switch Local vs API

Pour implémenter ce que tu as en tête, la modification se ferait dans la barre latérale de ton application :

> **Interface :** Un bouton radio `st.sidebar.radio("Mode d'intelligence", ["Cloud (Groq)", "Local (Ollama)"])`. <br>
> **Logique :** Si "Local" est choisi, le code instancie `ChatOllama(model="llama3")` au lieu de `ChatGroq`. Cela permet à une entreprise de traiter des documents ultra-confidentiels sans jamais utiliser internet.

**Souhaites-tu que je te prépare le code du sélecteur (Phase 4) pour l'intégrer dans ta barre latérale Streamlit ?** 🔮