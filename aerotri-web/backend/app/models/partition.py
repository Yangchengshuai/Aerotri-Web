"""Partition model for large-scale SfM blocks."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class BlockPartition(Base):
    """Per-block partition definition and SfM status."""

    __tablename__ = "block_partitions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Parent block
    block_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("blocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Partition index within block (0-based)
    index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Human-readable name, e.g. "P1", "P2"
    name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Image name range (sorted by filename)
    image_start_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image_end_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Basic statistics
    image_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    overlap_with_prev: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    overlap_with_next: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Status & progress for this partition's mapper
    status: Mapped[Optional[str]] = mapped_column(
        String(32),  # PENDING/RUNNING/COMPLETED/FAILED
        nullable=True,
    )
    progress: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        default=0.0,
    )

    # JSON statistics & last error message
    statistics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "block_id": self.block_id,
            "index": self.index,
            "name": self.name,
            "image_start_name": self.image_start_name,
            "image_end_name": self.image_end_name,
            "image_count": self.image_count,
            "overlap_with_prev": self.overlap_with_prev,
            "overlap_with_next": self.overlap_with_next,
            "status": self.status,
            "progress": self.progress,
            "statistics": self.statistics,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


