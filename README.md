🚀 Cosmo RAG — Assistant Virtuel Intelligent

Cosmo RAG est une application web complète de Retrieval-Augmented Generation (RAG). Elle permet d'ingérer des documents (PDF, DOCX) ou des données en provenance d'API REST pour poser des questions en langage naturel et obtenir des réponses précises basées exclusivement sur vos données.

🛠️ Stack Technique

- Frontend : React 18, TypeScript, Tailwind CSS, Lucide Icons, Vite
- Backend : Python 3.10+, FastAPI, Uvicorn
- Orchestration RAG : LangChain
- Embeddings & Vector DB : HuggingFace (sentence-transformers/all-MiniLM-L6-v2), ChromaDB
- LLM (Grand Modèle de Langage) : Groq API (openai/gpt-oss-20b)

📁 Structure du Projet
cosmo/
├── .env                  # Variables d'environnement Backend (ex: GROQ_API_KEY)
├── .gitignore            # Fichiers ignorés par Git
├── README.md             # Documentation du projet
├── requirements.txt      # Dépendances Python
├── backend/              # Code source API FastAPI
│   ├── main.py           # Endpoints REST & CORS
│   └── ingest.py         # Logique d'ingestion et découpage de texte
└── frontend/             # Application React Vite
    ├── .env.local        # Variables d'environnement Frontend
    ├── public/           # Assets statiques (images, avatars)
    └── src/
        └── App.tsx       # Interface utilisateur principale

⚙️ Installation et Configuration en Local

1. Prérequis
 -Python 3.10+
 -Node.js 18+ & npm

2. Configuration du Backend
 -Cloner le projet
  git clone <https://github.com/votre-compte/cosmo-rag.git>
 -cd cosmo-rag

 -Créer et activer l'environnement virtuel Python

# Windows (PowerShell)

 python -m venv venv
 .\venv\Scripts\Activate.ps1

 -Installer les dépendances
  pip install -r requirements.txt

 -Variables d'environnement (.env)
  Créez un fichier .env à la racine du projet :
  GROQ_API_KEY=votre_cle_groq_ici
  ALLOWED_ORIGINS=<http://localhost:5173>

 -Lancer le serveur Backend
  uvicorn backend.main:app --reload --port 8000L'API sera accessible sur <http://localhost:8000> (Documentation Swagger sur <http://localhost:8000/docs>).

1. Configuration du Frontend

 -Accéder au dossier frontend
  cd frontend

 -Installer les packages npm
  npm install

 -Variables d'environnement (.env.local)
  Créez un fichier .env.local dans le dossier frontend/ :
  VITE_API_URL=<http://localhost:8000>

 -Lancer le serveur de développement React
  npm run devL'application sera accessible sur <http://localhost:5173>.
  
  🚀 Build et Déploiement en Production

 -Build Frontend
  cd frontend
  npm run build
  Les fichiers statiques prêts pour la production se trouveront dans le dossier frontend/dist/.

    Serveur Backend Production
  uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2

📄 Licence
Ce projet est sous licence MIT.
