import psycopg
from pgvector.psycopg import register_vector

# Connexion à la base Docker
conn = psycopg.connect(
    dbname="vector_app_db",
    user="admin",
    password="supersecret",
    host="localhost",
    port="5432"
)

# Configuration pour gérer les vecteurs automatiquement
register_vector(conn)

# --- SCÉNARIO 1 : INSERTION (ALIMENTATION) ---
# Imaginons que ceci est un vecteur généré par une IA (ex: OpenAI)
# Pour l'exemple, c'est un vecteur aléatoire de taille 3 (au lieu de 1536 pour simplifier)
fake_embedding = [0.1, 0.3, 0.9]
content_text = "La capitale de la Belgique est Bruxelles."

with conn.cursor() as cur:
    cur.execute(
        "INSERT INTO documents (content, embedding) VALUES (%s, %s)",
        (content_text, fake_embedding)
    )
    conn.commit()

# --- SCÉNARIO 2 : RECHERCHE (POUR L'IA) ---
# Le vecteur de la question de l'utilisateur
user_query_vector = [0.1, 0.2, 0.8]

with conn.cursor() as cur:
    # L'opérateur <=> calcule la distance cosinus (le plus proche = le plus petit chiffre)
    cur.execute("""
                SELECT content, embedding <=> %s AS distance
                FROM documents
                ORDER BY distance ASC
                LIMIT 1
                """, (user_query_vector,))

    result = cur.fetchone()
    print(f"Meilleur résultat trouvé : {result[0]} (Distance: {result[1]})")

conn.close()