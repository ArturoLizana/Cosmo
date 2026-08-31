import os
import shutil
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=dotenv_path)

# --- PLANIFICATEUR ET SUPPRESSION AUTOMATIQUE (2h) ---

def clear_chroma_db():
    from backend.ingest import CHROMA_DB_DIR
    if os.path.exists(CHROMA_DB_DIR):
        try:
            shutil.rmtree(CHROMA_DB_DIR)
            print("🧹 ChromaDB a été réinitialisé automatiquement (toutes les 2h).")
        except Exception as e:
            print(f"Erreur lors de la suppression de ChromaDB : {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Démarrage du planificateur
    scheduler = BackgroundScheduler()
    scheduler.add_job(clear_chroma_db, 'interval', hours=2)
    scheduler.start()
    yield
    # Arrêt du planificateur lors de l'arrêt de FastAPI
    scheduler.shutdown()

# --- INITIALISATION DE L'APPLICATION ---

app = FastAPI(
    title="Cosmo RAG",
    description="API & Interface Chatbot RAG",
    version="1.0.0",
    lifespan=lifespan
)

raw_origins = os.getenv("ALLOWED_ORIGINS", "https://cosmo.arlidev.fr,http://localhost:5173")
ALLOWED_ORIGINS = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

embeddings_instance = None

def get_embeddings():
    global embeddings_instance
    if embeddings_instance is None:
        embeddings_instance = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    return embeddings_instance

groq_api_key = os.getenv("GROQ_API_KEY", "")
llm = ChatGroq(
    model_name="llama-3.1-8b-instant", 
    temperature=0, 
    groq_api_key=groq_api_key if groq_api_key else None
)

class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 3

class APIIngestRequest(BaseModel):
    url: str
    text_key: Optional[str] = None


# --- ENDPOINTS API ---

@app.post("/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
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
Si le contexte ne contient pas la réponse, réponds strictly : "L'information n'est pas présente dans les documents fournis."

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


# --- REDIRECTION FRONTEND REACT ---

frontend_dist = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))

if os.path.exists(frontend_dist):
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path in ["docs", "redoc", "openapi.json"] or full_path.startswith("docs/"):
        raise HTTPException(status_code=404, detail="Not Found")
        
    file_path = os.path.join(frontend_dist, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
        
    return FileResponse(os.path.join(frontend_dist, "index.html"))