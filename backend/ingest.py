import os
import requests
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.documents import Document

# Chemin de stockage de la base vectorielle ChromaDB
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_DIR = os.path.join(BASE_DIR, "..", "chroma_db")

_embeddings = None

def get_embeddings():
    """Initialise le modèle d'embeddings FastEmbed de manière différée (lazy-loading)."""
    global _embeddings
    if _embeddings is None:
        _embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    return _embeddings


def ingest_source(source_path_or_url: str, is_api: bool = False, api_text_key: Optional[str] = None):
    """Charge un fichier (.pdf/.docx) ou une API JSON, puis indexe les données dans ChromaDB."""
    documents = []

    if is_api:
        # Traitement d'une source API distante
        response = requests.get(source_path_or_url)
        response.raise_for_status()
        data = response.json()

        if api_text_key and isinstance(data, dict):
            content = str(data.get(api_text_key, data))
        elif isinstance(data, list):
            content = "\n".join([str(item) for item in data])
        else:
            content = str(data)

        documents = [Document(page_content=content, metadata={"source": source_path_or_url})]
    else:
        # Traitement d'un fichier local (.pdf ou .docx)
        ext = os.path.splitext(source_path_or_url)[1].lower()
        if ext == ".pdf":
            loader = PyPDFLoader(source_path_or_url)
            documents = loader.load()
        elif ext == ".docx":
            loader = Docx2txtLoader(source_path_or_url)
            documents = loader.load()
        else:
            raise ValueError(f"Format de fichier non supporté : {ext}")

    if not documents:
        raise ValueError("Aucun contenu extrait de la source.")

    # Découpage du texte en segments (chunks)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(documents)

    # Sauvegarde dans ChromaDB
    embeddings = get_embeddings()
    Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory=CHROMA_DB_DIR
    )

    return len(splits)