from sqlalchemy import String, Integer, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin


class KnowledgeSource(Base, TimestampMixin):
    """Fuente de conocimiento de un chatbot: texto, FAQ, URL o archivo."""
    __tablename__ = "knowledge_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False)
    chatbot_id: Mapped[int] = mapped_column(ForeignKey("chatbots.id", ondelete="CASCADE"), index=True, nullable=False)

    type: Mapped[str] = mapped_column(String(20), nullable=False)   # text|faq|url|txt|csv|pdf
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)   # texto crudo (para type=text/faq)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending|processing|ready|error
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class KnowledgeChunk(Base):
    """Fragmento de una fuente + su embedding (para recuperación por
    similitud). El embedding se guarda como JSON para correr en SQLite y en
    Postgres; en producción con pgvector se migra a columna vector."""
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("knowledge_sources.id", ondelete="CASCADE"), index=True, nullable=False)
    chatbot_id: Mapped[int] = mapped_column(ForeignKey("chatbots.id", ondelete="CASCADE"), index=True, nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)

    source: Mapped["KnowledgeSource"] = relationship(back_populates="chunks")
