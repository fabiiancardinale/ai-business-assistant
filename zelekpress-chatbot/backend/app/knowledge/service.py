"""Servicio de Knowledge Base (RAG).

Pipeline: extraer texto -> chunking -> embeddings -> guardar. En consulta:
embeber la pregunta -> similitud coseno contra los chunks del chatbot ->
top-k -> inyectar en el prompt.

El procesamiento se hace de forma síncrona (suficiente para textos/URLs). Si
en el futuro hay documentos grandes, se mueve a un worker (RQ/Celery) sin
cambiar esta interfaz."""
from __future__ import annotations

import re

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.ai.embeddings import get_embedder, cosine
from app.models.knowledge import KnowledgeSource, KnowledgeChunk

CHUNK_SIZE = 600      # caracteres por chunk (aprox)
CHUNK_OVERLAP = 100
TOP_K = 4


# ---------------------- extracción de texto ----------------------

def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_url(url: str) -> str:
    import requests
    r = requests.get(url, timeout=20, headers={"User-Agent": "ZelekpressBot/1.0"})
    r.raise_for_status()
    return _strip_html(r.text)


def extract_file(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(data))
            return "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"No se pudo leer el PDF: {e}")
    # txt, csv, md, etc. -> texto plano
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return data.decode("latin-1", errors="ignore")


# ---------------------- chunking ----------------------

def chunk_text(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + CHUNK_SIZE, n)
        # cortar en un espacio cercano para no partir palabras
        if end < n:
            sp = text.rfind(" ", start + CHUNK_SIZE - CHUNK_OVERLAP, end)
            if sp > start:
                end = sp
        chunks.append(text[start:end].strip())
        if end >= n:
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return [c for c in chunks if c]


# ---------------------- ingest ----------------------

def process_source(db: Session, source: KnowledgeSource) -> None:
    """Extrae, chunkea, embebe y guarda. Actualiza el estado de la fuente."""
    source.status = "processing"
    db.commit()

    # borrar chunks previos (reprocesar)
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source_id == source.id))
    db.commit()

    try:
        if source.type == "url" and source.url:
            text = extract_url(source.url)
        else:
            text = source.content or ""

        chunks = chunk_text(text)
        embedder = get_embedder()
        for i, ch in enumerate(chunks):
            db.add(KnowledgeChunk(
                source_id=source.id, chatbot_id=source.chatbot_id, company_id=source.company_id,
                position=i, content=ch, embedding=embedder.embed(ch),
            ))
        source.chunk_count = len(chunks)
        source.size = len(text)
        source.status = "ready"
        source.error = None
        db.commit()
    except Exception as e:  # noqa: BLE001
        source.status = "error"
        source.error = str(e)[:500]
        db.commit()


# ---------------------- retrieval ----------------------

# Umbral mínimo de similitud para considerar un chunk "relevante".
MIN_SCORE = 0.12


def retrieve(db: Session, chatbot_id: int, query: str, k: int = TOP_K) -> list[str]:
    """Devuelve los fragmentos más relevantes para la pregunta."""
    q = query.strip()
    if not q:
        return []
    rows = db.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.chatbot_id == chatbot_id)
    ).scalars().all()
    if not rows:
        return []

    qvec = get_embedder().embed(q)
    scored = [(cosine(qvec, ch.embedding or []), ch.content) for ch in rows]
    scored = [(s, c) for s, c in scored if s > MIN_SCORE]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:k]]


def has_sources(db: Session, chatbot_id: int) -> bool:
    from sqlalchemy import func
    n = db.scalar(select(func.count()).select_from(KnowledgeSource)
                  .where(KnowledgeSource.chatbot_id == chatbot_id)) or 0
    return n > 0


def record_unanswered(db: Session, company_id: int, chatbot_id: int, question: str) -> None:
    """Registra (dedupe + contador) una pregunta que la KB no cubrió."""
    import re as _re
    from app.models.analytics import UnansweredQuestion
    norm = _re.sub(r"\s+", " ", question.strip().lower())[:300]
    if not norm:
        return
    existing = db.scalar(select(UnansweredQuestion).where(
        UnansweredQuestion.chatbot_id == chatbot_id,
        UnansweredQuestion.question_norm == norm,
    ))
    if existing:
        existing.count += 1
        existing.resolved = False
    else:
        db.add(UnansweredQuestion(
            company_id=company_id, chatbot_id=chatbot_id,
            question=question.strip()[:1000], question_norm=norm,
        ))
    db.commit()
