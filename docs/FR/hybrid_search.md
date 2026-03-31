# Recherche Hybride

La **recherche hybride** est une technique avancée que nous utilisons pour interroger notre base de connaissances. Elle combine le meilleur de deux mondes : la **recherche sémantique (vectorielle)** et la **recherche par mots-clés (Full-Text Search)**. Cette approche offre des résultats de recherche beaucoup plus pertinents et nuancés qu'une seule méthode utilisée isolément.

Cette fonctionnalité est principalement utilisée lorsque l'application est déployée en **mode Cloud** avec **Supabase** et son extension `pgvector`.

## 1. Les Deux Piliers de la Recherche Hybride

### a) Recherche Sémantique (Vectorielle)

-   **Comment ça marche ?** : Chaque morceau de texte (chunk) dans notre base de données est associé à un **vecteur (embedding)** qui représente sa signification sémantique. Lorsqu'un utilisateur pose une question, nous transformons également cette question en vecteur. La recherche consiste alors à trouver les chunks dont les vecteurs sont les plus "proches" (généralement par similarité cosinus) du vecteur de la question.
-   **Avantages** :
    -   Comprend le **contexte** et l'**intention** derrière la recherche.
    -   Trouve des résultats pertinents même s'ils n'utilisent pas les mêmes mots-clés. Par exemple, une recherche sur "comment gagner de l'argent" pourrait trouver un document parlant de "générer des revenus".
-   **Inconvénients** : Peut parfois manquer des résultats où un mot-clé très spécifique (comme un nom de produit, un code d'erreur ou un acronyme) est important.

### b) Recherche par Mots-Clés (BM25 / Full-Text Search)

-   **Comment ça marche ?** : C'est la méthode de recherche "traditionnelle". Le système recherche les documents qui contiennent les mots-clés exacts de la requête. Des algorithmes comme **BM25** (Best Matching 25) classent les documents en fonction de la fréquence et de la rareté des termes recherchés.
-   **Avantages** :
    -   Très efficace pour trouver des correspondances exactes et des termes rares.
    -   Indispensable lorsque la précision d'un mot-clé est primordiale.
-   **Inconvénients** :
    -   Ne comprend pas les synonymes ou le contexte. Une recherche sur "voiture" ne trouvera pas un document qui ne mentionne que le mot "automobile".
    -   Peut être submergée par des termes très courants.

## 2. La Fusion : Reciprocal Rank Fusion (RRF)

La magie de la recherche hybride réside dans la manière dont elle combine les résultats des deux méthodes. Nous ne nous contentons pas de prendre les X premiers résultats de chaque liste. Nous utilisons une technique de fusion sophistiquée appelée **Reciprocal Rank Fusion (RRF)**.

-   **Principe** : RRF donne un score à chaque document en fonction de sa **position (rang)** dans les listes de résultats de chaque méthode de recherche, plutôt qu'en fonction de son score de pertinence interne.
-   **Formule (simplifiée)** : Pour chaque document, son score RRF est la somme de `1 / (k + rang)`, où `rang` est sa position dans chaque liste de résultats et `k` est une constante (souvent 60).
-   **Avantages de RRF** :
    -   **Équitable** : Elle ne favorise pas une méthode de recherche par rapport à une autre. Un document qui apparaît dans le top 3 des deux recherches obtiendra un score très élevé.
    -   **Robuste** : Elle est moins sensible aux scores de pertinence parfois mal calibrés d'une seule méthode.
    -   **Met en avant la pertinence croisée** : Les documents jugés pertinents par les deux approches (sémantique ET par mot-clé) sont naturellement favorisés et remontent en haut de la liste finale.

En conclusion, la recherche hybride nous permet de fournir à notre agent IA un contexte RAG (Retrieval-Augmented Generation) de bien meilleure qualité. Elle combine la compréhension sémantique profonde de la recherche vectorielle avec la précision chirurgicale de la recherche par mots-clés, garantissant que les informations les plus pertinentes sont trouvées, quel que soit le type de question posée par l'utilisateur.