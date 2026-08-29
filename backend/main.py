import os
import shutil
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_groq import ChatGroq
from dotenv import load_dotenv

# Chargement des variables d'environnement (.env)
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=dotenv_path)

app = FastAPI(
    title="Cosmo",
    description="API REST pour le traitement de documents et le RAG",
    version="1.0.0"
)

# Configuration CORS
raw_origins = os.getenv("ALLOWED_ORIGINS", "https://cosmo.arlidev.fr,http://localhost:5173")
ALLOWED_ORIGINS = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permet la communication cross-origin globale
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singleton pour le modèle d'embeddings (chargement différé)
embeddings_instance = None

def get_embeddings():
    """Charge le modèle d'embeddings FastEmbed uniquement à la première requête."""
    global embeddings_instance
    if embeddings_instance is None:
        embeddings_instance = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    return embeddings_instance

# Initialisation du modèle Groq (LLM)
groq_api_key = os.getenv("GROQ_API_KEY", "")
llm = ChatGroq(
    model_name="llama-3.1-8b-instant", 
    temperature=0, 
    groq_api_key=groq_api_key if groq_api_key else None
)

# Schémas de données Pydantic
class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 3

class APIIngestRequest(BaseModel):
    url: str
    text_key: Optional[str] = None


# Endpoints API

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API Cosmo RAG. Consultez /docs pour la documentation Swagger."}


@app.post("/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
    # Import local pour éviter l'import circulaire au démarrage
    from backend.ingest import ingest_source
    
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
        splits_count = ingest_source(file_path)
        return {
            "status": "success",
            "message": f"Fichier '{file.filename}' indexé avec succès ({splits_count} segments créés).",
            "path": file_path
        }
    except Exception as e:
        print(f"Erreur d'ingestion : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur d'ingestion : {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@app.post("/ingest/api")
async def ingest_api(request: APIIngestRequest):
    # Import local pour éviter l'import circulaire au démarrage
    from backend.ingest import ingest_source
    
    try:
        splits_count = ingest_source(request.url, is_api=True, api_text_key=request.text_key)
        return {
            "status": "success",
            "message": f"Données de l'API '{request.url}' indexées avec succès ({splits_count} segments créés)."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'ingestion API : {str(e)}")


@app.post("/query")
async def query_rag(request: QueryRequest):
    # Import local pour la constante du répertoire ChromaDB
    from backend.ingest import CHROMA_DB_DIR

    if not os.path.exists(CHROMA_DB_DIR):
        raise HTTPException(
            status_code=400, 
            detail="La base de données vectorielle est vide. Veuillez d'abord ingérer des documents."
        )

    try:
        embeddings = get_embeddings()
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

        return {
            "answer": answer_text
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement : {str(e)}")