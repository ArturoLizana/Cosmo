import os
import shutil
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_community.vectorstores import Chroma
# from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# 1. Charger les variables d'environnement depuis le .env à la racine
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=dotenv_path)

# Import du module d'ingestion local
from backend.ingest import ingest_source, CHROMA_DB_DIR

app = FastAPI(
    title="Cosmo",
    description="API REST pour le traitement de documents et le RAG (PDF, Word, API JSON)",
    version="1.0.0"
)

# Gestion dynamique des origines CORS
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", 
    "https://cosmo.arlidev.fr,http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chargement du modèle d'embedding (local)
# embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Chargement du modèle d'embedding (version légère compatible avec Render)
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

# 2. Récupérer la clé d'API depuis .env
groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("La variable GROQ_API_KEY est introuvable ou vide dans le fichier .env")

# Injection dans les variables d'environnement système pour LangChain/Groq
os.environ["GROQ_API_KEY"] = groq_api_key

# 3. Initialisation du modèle Groq
llm = ChatGroq(model_name="openai/gpt-oss-20b", temperature=0)

class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 3

class APIIngestRequest(BaseModel):
    url: str
    text_key: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API Cosmo RAG. Consultez /docs pour la documentation Swagger."}

@app.post("/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
    """Endpoint pour ingérer un fichier PDF ou Word téléversé."""
    allowed_extensions = [".pdf", ".docx"]
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail="Extension non supportée. Seuls les fichiers .pdf et .docx sont acceptés."
        )

    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        ingest_source(file_path)
        return {
            "status": "success",
            "message": f"Fichier '{file.filename}' indexé avec succès.",
            "path": file_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'ingestion : {str(e)}")

@app.post("/ingest/api")
async def ingest_api(request: APIIngestRequest):
    """Endpoint pour ingérer le contenu JSON d'une API REST externe."""
    try:
        ingest_source(request.url, is_api=True, api_text_key=request.text_key)
        return {
            "status": "success",
            "message": f"Données de l'API '{request.url}' indexées avec succès."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'ingestion API : {str(e)}")

@app.post("/query")
async def query_rag(request: QueryRequest):
    """Endpoint pour poser une question au RAG."""
    if not os.path.exists(CHROMA_DB_DIR):
        raise HTTPException(
            status_code=400, 
            detail="La base de données vectorielle est vide. Veuillez d'abord ingérer des documents."
        )

    try:
        vectorstore = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=embeddings)
        retriever = vectorstore.as_retriever(search_kwargs={"k": request.top_k})

        docs = retriever.invoke(request.question)

        if not docs:
            return {
                "answer": "Aucun document pertinent trouvé dans la base de connaissances."
            }

        context_text = "\n\n---\n\n".join([doc.page_content for doc in docs])

        prompt = f"""Tu es un assistant virtuel d'entreprise rigoureux.
Réponds à la question en t'appuyant uniquement sur le contexte ci-dessous.
Si le contexte ne contient pas la réponse, réponds strictement : "L'information n'est pas présente dans les documents fournis."

Contexte :
{context_text}

Question : {request.question}
Réponse :"""

        response = llm.invoke(prompt)
        answer_text = response.content if hasattr(response, "content") else str(response)

        sources = [
            {
                "source": doc.metadata.get("source", "Inconnue"),
                "page": doc.metadata.get("page", None)
            }
            for doc in docs
        ]

        return {
            "answer": answer_text,
            #"sources": sources
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement : {str(e)}")