# HELMo Oracle — Guide Complet

---

## PARTIE 1 — Présentation de l'Architecture (pour la direction)

### Contexte et décision technique

Le projet HELMo Oracle est un assistant intelligent de type RAG (Retrieval-Augmented Generation). Il interroge une base de données de documents vectorisés pour répondre aux questions des utilisateurs en s'appuyant uniquement sur les archives ingérées — sans hallucination.

Initialement développé sur Streamlit Cloud (solution tout-en-un mais limitée), nous avons fait évoluer l'architecture vers une solution **production-ready** séparant clairement le backend et le frontend.

### Architecture retenue

```
┌─────────────────────┐         HTTPS          ┌──────────────────────┐
│   Frontend (Vercel) │ ──────────────────────► │  Backend (VPS Docker)│
│   HTML / JS statique│                         │  FastAPI + Python    │
│   helmo-oracle.     │                         │  api.dlzteam.com     │
│   vercel.app        │                         │  Port 443 (Nginx)    │
└─────────────────────┘                         └──────────┬───────────┘
                                                           │
                                                           ▼
                                                ┌──────────────────────┐
                                                │  Supabase (pgvector) │
                                                │  Base vectorielle    │
                                                │  PostgreSQL cloud    │
                                                └──────────────────────┘
```

### Pourquoi cette architecture ?

| Critère | Ancienne solution | Nouvelle solution |
|---|---|---|
| **Déploiement** | Tout-en-un Streamlit (limité) | Backend VPS Docker + Frontend Vercel |
| **Frontend** | Couplé au backend Python | Découplé sur Vercel (CDN mondial) |
| **Scalabilité** | Non | Oui — Docker facilement migrable |
| **Portabilité** | Dépendant de Streamlit | Plug & play sur n'importe quel serveur |
| **Maintenabilité** | Difficile | Git push → Vercel auto-déploie le front, git pull sur VPS pour le back |

### Solution Plug & Play

Grâce à Docker, déployer l'Oracle sur un nouveau serveur se résume à :

1. Installer Docker sur le serveur
2. Cloner le repo Git
3. Copier les fichiers de configuration (`config.yaml` + `prompt.txt`)
4. Lancer `docker compose up -d --build`

C'est tout. L'application tourne en moins de 15 minutes sur n'importe quel serveur Linux avec Docker.

---

## PARTIE 2 — Guide Développement Local (pour les collègues)

### Prérequis

- Python 3.12
- Git
- Un terminal (PowerShell sur Windows)
- Un fichier `config.yaml` valide (demandez-le à un membre de l'équipe)

### Installation

**1. Cloner le repo**
```bash
git clone https://github.com/dlz-dev/HELMo-ORACLE.git
cd HELMo-ORACLE
git checkout develop
```

**2. Créer l'environnement virtuel**
```bash
python -m venv .venv

# Windows
.\.venv\Scripts\Activate.ps1

# Mac / Linux
source .venv/bin/activate
```

**3. Installer les dépendances**
```bash
pip install -r requirements.txt
```

**4. Télécharger le modèle spaCy**
```bash
python -m spacy download fr_core_news_sm
```

**5. Configurer**
```bash
# Copier et remplir le fichier de config (clés API, base de données)
copy config\config.example.yaml config\config.yaml

# Copier et personnaliser le prompt système
copy config\prompt.example.txt config\prompt.txt
```

Ouvrez `config/config.yaml` et remplissez :
- `database.connection_string` — la chaîne de connexion Supabase
- Les clés API des providers LLM que vous souhaitez utiliser (Groq, OpenAI, Anthropic, etc.)

### Lancer en local

**Terminal 1 — Backend FastAPI**
```bash
uvicorn api:app --port 8000
```

Le backend est disponible sur `http://localhost:8000`

**Terminal 2 — Frontend**
```bash
cd frontend
python -m http.server 8080
```

Ouvrez `http://localhost:8080` dans votre navigateur.

> ⚠️ Ne pas ouvrir `index.html` directement en `file://` — les navigateurs bloquent les requêtes fetch depuis un fichier local.

Dans les **Paramètres** (⚙️) de l'interface, vérifiez que l'URL du backend est bien `http://localhost:8000`.

### Vérifier que tout fonctionne

```bash
curl http://localhost:8000/health
# Doit retourner : {"status":"ok"}
```

### Ingérer des données en local

Placez vos fichiers dans `data/files/` avec le préfixe `lore_` puis lancez :

```bash
python -m core.pipeline.ingestion
```

### Workflow Git

```
develop  ──── feature branch ──── PR vers develop ──── merge vers main (prod)
```

- `develop` → branche de développement, déployée automatiquement sur Vercel (preview)
- `main` → branche de production, déployée sur Vercel (prod) + récupérée manuellement sur le VPS

---

## PARTIE 3 — Gestion du Serveur VPS

### Accès SSH

```bash
ssh root@64.226.121.243
```

Le backend tourne sur `https://api.dlzteam.com` (Nginx reverse proxy → port 8000).

---

### Commandes Docker essentielles

| Action | Commande |
|---|---|
| Voir l'état des containers | `docker compose ps` |
| Démarrer | `docker compose start` |
| Arrêter | `docker compose stop` |
| Redémarrer | `docker compose restart` |
| Voir les logs en direct | `docker compose logs -f` |
| Voir les 50 dernières lignes | `docker compose logs --tail=50` |
| Rebuild et redémarrer | `docker compose up -d --build` |

---

### Modifier le prompt système

```bash
nano ~/HELMo-ORACLE/config/prompt.txt
```

`Ctrl+O` pour sauvegarder, `Ctrl+X` pour quitter. Puis :

```bash
cd ~/HELMo-ORACLE && docker compose restart
```

---

### Modifier la configuration (clés API, DB, paramètres)

```bash
nano ~/HELMo-ORACLE/config/config.yaml
```

Puis :
```bash
cd ~/HELMo-ORACLE && docker compose restart
```

---

### Workflow de mise à jour du code

#### Modification du frontend uniquement (HTML/JS)

**Sur votre PC :**
```bash
git add frontend/
git commit -m "feat: description du changement"
git push origin develop
```

Vercel redéploie automatiquement. **Rien à faire sur le VPS.**

#### Modification du backend (Python, api.py, core/, etc.)

**Sur votre PC :**
```bash
git add .
git commit -m "feat: description du changement"
git push origin develop
```

**Sur le VPS :**
```bash
cd ~/HELMo-ORACLE
git pull origin develop    # ou main en production
docker compose up -d --build
```

#### Résumé

| Type de modification | Action VPS nécessaire |
|---|---|
| `prompt.txt` / `config.yaml` | `docker compose restart` |
| Code Python / `api.py` / `core/` | `git pull` + `docker compose up -d --build` |
| Frontend uniquement | Rien (Vercel auto-déploie) |

---

### Ingestion de nouveaux fichiers

**1. Envoyer les fichiers depuis votre PC**
```powershell
# Un seul fichier
scp "C:\chemin\fichier.json" root@64.226.121.243:~/HELMo-ORACLE/data/new_files/lore_fichier.json

# Un dossier entier
scp -r "C:\chemin\dossier\*" root@64.226.121.243:~/HELMo-ORACLE/data/new_files/
```

> ⚠️ Les fichiers doivent avoir le préfixe `lore_` pour être traités.

**2. Lancer le watcher sur le VPS**
```bash
docker compose exec oracle-backend python watcher.py
```

Le watcher valide, ingère et archive chaque fichier. `Ctrl+C` quand c'est terminé.

**3. Vérifier l'ingestion**
```bash
curl https://api.dlzteam.com/archives
```

---

### Gestion des coûts — Snapshot & Restore

Pour économiser quand le serveur n'est pas utilisé, la meilleure option est de faire un **snapshot** puis de **détruire** le droplet.

**Créer un snapshot (depuis le VPS puis DigitalOcean)**
```bash
# Sur le VPS — éteindre proprement
poweroff
```

Puis dans le dashboard DigitalOcean : **Snapshots** → **Take Snapshot**.

**Restaurer depuis un snapshot**
1. Dashboard DigitalOcean → **Create Droplet**
2. Onglet **Snapshots** → sélectionnez votre snapshot
3. Choisissez la même taille (2vCPU / 4GB)
4. **Create**
5. Récupérez la nouvelle IP dans le dashboard
6. Mettez à jour le DNS Cloudflare : record `api` → nouvelle IP
7. Attendez 2 minutes, testez : `curl https://api.dlzteam.com/health`

> Le watcher ne redémarre pas automatiquement après restore. Relancez-le si besoin :
> ```bash
> cd ~/HELMo-ORACLE && docker compose exec -d oracle-backend python watcher.py
> ```

---

### Déployer sur un nouveau serveur (from scratch)

```bash
# 1. Installer Docker (Ubuntu)
apt-get update
apt-get install -y docker.io docker-compose-plugin

# 2. Cloner le repo
git clone https://github.com/dlz-dev/HELMo-ORACLE.git
cd HELMo-ORACLE
git checkout main

# 3. Copier les fichiers de config (via SCP depuis votre PC)
# scp config.yaml root@IP:~/HELMo-ORACLE/config/config.yaml
# scp prompt.txt root@IP:~/HELMo-ORACLE/config/prompt.txt

# 4. Créer les dossiers
mkdir -p storage/sessions data/new_files data/files data/quarantine

# 5. Lancer
docker compose up -d --build

# 6. Configurer HTTPS (si domaine disponible)
apt-get install -y nginx certbot python3-certbot-nginx
# ... (voir section Nginx ci-dessous)
```

### Configuration Nginx + HTTPS

```bash
# Créer la config
cat > /etc/nginx/sites-available/oracle << 'EOF'
server {
    listen 80;
    server_name api.votredomaine.com;
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

ln -s /etc/nginx/sites-available/oracle /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# Ouvrir les ports
ufw allow 80
ufw allow 443

# Certificat HTTPS
certbot --nginx -d api.votredomaine.com
```

> Prérequis : un enregistrement DNS de type `A` pointant vers l'IP du serveur doit exister avant de lancer certbot.
