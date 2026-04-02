# 🔒 Documentation de Sécurité : Row Level Security (RLS) avec Supabase

## 1. Contexte et Architecture
Dans le cadre de notre application RAG, plusieurs utilisateurs interagissent avec notre IA. Afin de garantir la confidentialité des données (historique de chat, feedbacks, profils), nous utilisons le Row Level Security (RLS) de PostgreSQL, géré via Supabase.

Notre architecture a la particularité de séparer les responsabilités :
* **Base Vectorielle (Documents) :** Gérée par le backend FastAPI (connecté à pgvector, par exemple sur Digital Ocean). Aucune interaction directe depuis le front-end n'est permise ; le backend agit comme un proxy sécurisé disposant de droits complets.
* **Base Utilisateurs (Supabase) :** Gère l'authentification, les sessions de chat, les logs et les retours (feedbacks). C'est ici que le RLS s'applique strictement pour isoler les données entre les différents utilisateurs.

## 2. Flux d'Authentification (OAuth)
1. L'utilisateur se connecte via le frontend en utilisant l'authentification Supabase (OAuth).
2. Supabase génère un JWT (JSON Web Token) contenant l'identifiant unique de l'utilisateur, accessible via `auth.uid()`.
3. Ce JWT est transmis lors de chaque requête vers la base de données Supabase.
4. Les politiques RLS (Policies) évaluent ce JWT en temps réel pour vérifier si le `auth.uid()` correspond au `user_id` de la ligne ciblée.

## 3. Matrice de Sécurité par Table

| Table | Rôle Authentifié (Frontend) | Rôle Anonyme (Non authentifié) | Backend API (Service Role) |
| :--- | :--- | :--- | :--- |
| `documents` | ❌ Aucun accès direct (requêtes via API) | ❌ Aucun accès | ✅ Lecture/Écriture complète |
| `chat_sessions` | ✅ CRUD complet (sur ses propres sessions *uniquement*) | ❌ Aucun accès | ✅ Accès complet |
| `feedback` | ✅ INSERT (sur ses propres feedbacks) | ❌ Aucun accès | ✅ Accès complet |
| `profiles` | ✅ SELECT et UPDATE (sur son propre profil) | ❌ Aucun accès | ✅ Accès complet |
| `logs` | ✅ INSERT (si requis par le front) / ❌ Lecture | ❌ Aucun accès | ✅ Accès complet |

## 4. Implémentation des Politiques RLS (SQL)

Voici les règles de sécurité appliquées sur la base Supabase pour garantir l'isolation des données d'authentification et d'historique :

### Activation globale
Le RLS doit être activé explicitement sur les tables concernées.
```sql
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.logs ENABLE ROW LEVEL SECURITY;
```

### 4.1 Table chat_sessions (Historique des conversations)
Les utilisateurs ne peuvent voir, modifier ou supprimer que les sessions qui leur appartiennent.

```sql
CREATE POLICY "Les utilisateurs gèrent leurs propres sessions"
ON public.chat_sessions
FOR ALL
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);
```

### 4.2 Table feedback (Retours utilisateurs)
Un utilisateur connecté peut insérer un feedback, et le système s'assure qu'il est bien enregistré en son nom.

```sql
CREATE POLICY "Les utilisateurs peuvent donner un feedback"
ON public.feedback
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);
```

### 4.3 Table logs (Journalisation système)
Le frontend peut envoyer des logs d'erreurs vers la base de données (INSERT), mais la lecture de ces logs est strictement réservée au backend ou aux administrateurs.

```sql
CREATE POLICY "Insertion des logs depuis le front"
ON public.logs
FOR INSERT
TO authenticated
WITH CHECK (true);
```
