import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class ChunkType(str, enum.Enum):
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"


class Chunk(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    parent_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True
    )

    chunk_type: Mapped[ChunkType] = mapped_column(Enum(ChunkType, name="chunk_type"), default=ChunkType.TEXT)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str] = mapped_column(String(512), nullable=True)
    section_path: Mapped[str] = mapped_column(String(1024), nullable=True)

    # bounding box on the page, for highlight-on-citation-click: [x0, y0, x1, y1] in PDF points
    bbox: Mapped[list[float] | None] = mapped_column(JSONB, nullable=True)

    token_count: Mapped[int] = mapped_column(Integer, default=0)
    vector_id: Mapped[str] = mapped_column(String(64), nullable=True, index=True)

    document: Mapped["Document"] = relationship(back_populates="chunks")
