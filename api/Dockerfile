FROM python:3.12-slim

WORKDIR /app

# Dépendances système (build tools pour certains packages Python natifs)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python en premier (optimisation du cache Docker)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
RUN pip install --force-reinstall --no-deps python-multipart==0.0.12

# Télécharger le modèle spaCy français
RUN python -m spacy download fr_core_news_sm

# Copier le code source de l'API
COPY . .

# Créer explicitement le dossier logs
RUN mkdir -p logs

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]