"""Block model for aerotriangulation tasks."""
import enum
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Enum, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class BlockStatus(str, enum.Enum):
    """Block processing status."""
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AlgorithmType(str, enum.Enum):
    """Algorithm type for mapping."""
    COLMAP = "colmap"  # Incremental SfM
    GLOMAP = "glomap"  # Global SfM


class MatchingMethod(str, enum.Enum):
    """Feature matching method."""
    SEQUENTIAL = "sequential"
    EXHAUSTIVE = "exhaustive"
    VOCAB_TREE = "vocab_tree"
    SPATIAL = "spatial"


class Block(Base):
    """Block represents an aerotriangulation project/task."""
    
    __tablename__ = "blocks"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # User-provided source directory (never mutate files here)
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    # Explicit source path (kept for clarity / future compatibility)
    source_image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Per-block working directory (symlinks/hardlinks), safe to delete inside
    working_image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    status: Mapped[BlockStatus] = mapped_column(
        Enum(BlockStatus), 
        default=BlockStatus.CREATED,
        nullable=False
    )
    
    # Algorithm settings
    algorithm: Mapped[AlgorithmType] = mapped_column(
        Enum(AlgorithmType),
        default=AlgorithmType.GLOMAP,
        nullable=False
    )
    matching_method: Mapped[MatchingMethod] = mapped_column(
        Enum(MatchingMethod),
        default=MatchingMethod.SEQUENTIAL,
        nullable=False
    )
    
    # Parameters stored as JSON
    feature_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    matching_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    mapper_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Processing statistics
    statistics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Current processing stage and progress
    current_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # More granular stage (parsed from logs), optional
    current_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress: Mapped[Optional[float]] = mapped_column(nullable=True, default=0.0)
    
    # Error message if failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "name": self.name,
            "image_path": self.image_path,
            "source_image_path": self.source_image_path,
            "working_image_path": self.working_image_path,
            "output_path": self.output_path,
            "status": self.status.value,
            "algorithm": self.algorithm.value,
            "matching_method": self.matching_method.value,
            "feature_params": self.feature_params,
            "matching_params": self.matching_params,
            "mapper_params": self.mapper_params,
            "statistics": self.statistics,
            "current_stage": self.current_stage,
            "current_detail": self.current_detail,
            "progress": self.progress,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
