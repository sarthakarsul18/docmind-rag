"""
rag_backend.py
----------------
Core RAG (Retrieval Augmented Generation) engine for chatting with a PDF.

Responsibilities:
 - Load & chunk a PDF
 - Build / cache a FAISS vector index (on-disk, keyed by file hash so the
   same PDF is never re-embedded twice)
 - Build a retrieval chain powered by Groq (Llama 4 Scout)
 - Expose a streaming generator so the UI can show a live "typing" effect

"""

import os
import hashlib
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
VECTOR_DB_ROOT = "faiss_db"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

PROMPT_TEMPLATE = """You are a precise, friendly research assistant.
Answer the question using ONLY the information available in the context below.
If the answer isn't in the context, clearly say the document doesn't contain
that information. Never make anything up.

Context:
{context}

Question:
{question}

Write a clear, well-formed answer in 2-4 sentences.
"""

# Module-level singletons so models aren't reloaded on every Streamlit rerun
_embeddings = None
_llm_cache = {}


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return _embeddings


def get_llm(temperature: float = 0.2):
    """Cache one ChatGroq instance per temperature value used."""
    if temperature not in _llm_cache:
        _llm_cache[temperature] = ChatGroq(model=GROQ_MODEL, temperature=temperature)
    return _llm_cache[temperature]


def _file_hash(file_bytes: bytes) -> str:
    return hashlib.md5(file_bytes).hexdigest()[:12]


def get_cache_dir(file_bytes: bytes, filename: str) -> str:
    name = os.path.splitext(os.path.basename(filename))[0]
    safe_name = "".join(c for c in name if c.isalnum() or c in ("_", "-")) or "doc"
    return os.path.join(VECTOR_DB_ROOT, f"{safe_name}_{_file_hash(file_bytes)}")


def index_exists(cache_dir: str) -> bool:
    return os.path.isdir(cache_dir) and os.path.exists(os.path.join(cache_dir, "index.faiss"))


def build_or_load_vectorstore(pdf_path: str, file_bytes: bytes, filename: str, force_rebuild: bool = False):
    """
    Builds a FAISS index from a PDF, or loads it from an on-disk cache if the
    exact same file was already indexed before (same content hash).

    Returns: (vectorstore, num_chunks, cache_dir, loaded_from_cache: bool)
    """
    cache_dir = get_cache_dir(file_bytes, filename)
    embeddings = get_embeddings()

    if not force_rebuild and index_exists(cache_dir):
        vectorstore = FAISS.load_local(cache_dir, embeddings, allow_dangerous_deserialization=True)
        num_chunks = vectorstore.index.ntotal
        return vectorstore, num_chunks, cache_dir, True

    loader = PyPDFLoader(pdf_path)
    docs = loader.load()

    if not docs:
        raise ValueError("Couldn't extract any text from this PDF. It may be a scanned/image-only file.")

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.split_documents(docs)

    if not chunks:
        raise ValueError("No usable text chunks were produced from this PDF.")

    vectorstore = FAISS.from_documents(chunks, embeddings)
    os.makedirs(cache_dir, exist_ok=True)
    vectorstore.save_local(cache_dir)

    return vectorstore, len(chunks), cache_dir, False


def format_docs(docs) -> str:
    return "\n\n---\n\n".join(d.page_content for d in docs)


def build_chain(vectorstore, k: int = 3, temperature: float = 0.2):
    """Builds the retrieval -> prompt -> llm -> string chain."""
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    llm = get_llm(temperature)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain, retriever


def get_sources(retriever, question: str):
    """Returns the raw retrieved chunks, useful for a 'Sources used' UI panel."""
    return retriever.invoke(question)


def stream_answer(chain, question: str):
    """Generator that yields response chunks as they arrive from Groq."""
    for chunk in chain.stream(question):
        yield chunk


def ask_question(chain, question: str) -> str:
    """Non-streaming convenience helper."""
    return chain.invoke(question)