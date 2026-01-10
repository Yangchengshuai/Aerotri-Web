"""ReconVersion model for OpenMVS reconstruction version management."""
import enum
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, JSON, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class ReconVersionStatus(str, enum.Enum):
    """Reconstruction version status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ReconVersion(Base):
    """ReconVersion represents a single OpenMVS reconstruction run with specific parameters.
    
    Multiple versions can exist for a single Block, allowing comparison of different
    reconstruction settings (e.g., fast vs high quality).
    """
    
    __tablename__ = "recon_versions"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Foreign key to Block
    block_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("blocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Version index (1, 2, 3, ...) - auto-incremented per block
    version_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    
    # Version name (auto-generated or user-provided)
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # Quality preset used (fast/balanced/high)
    quality_preset: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="balanced",
    )
    
    # Custom parameters provided by user (may be None if using preset only)
    custom_params: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # Merged parameters (preset + custom overrides)
    merged_params: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ReconVersionStatus.PENDING.value,
    )
    
    # Progress (0-100)
    progress: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    
    # Current stage (undistort/convert/densify/mesh/refine/texture/completed)
    current_stage: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    
    # Output path for this version (e.g., {block_output}/recon/v1/)
    output_path: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Error message if failed
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # Statistics (stage times, file sizes, etc.)
    statistics: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "block_id": self.block_id,
            "version_index": self.version_index,
            "name": self.name,
            "quality_preset": self.quality_preset,
            "custom_params": self.custom_params,
            "merged_params": self.merged_params,
            "status": self.status,
            "progress": self.progress,
            "current_stage": self.current_stage,
            "output_path": self.output_path,
            "error_message": self.error_message,
            "statistics": self.statistics,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
