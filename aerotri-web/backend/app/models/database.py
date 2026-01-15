"""Database configuration and session management."""
import os
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from ..conf.settings import get_settings

# Load database path from configuration system
_settings = get_settings()
DATABASE_PATH = str(_settings.database.path)
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


async def init_db():
    """Initialize database tables."""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Lightweight schema migration for SQLite (no Alembic).
        # Keep this minimal: only ADD COLUMN when missing.
        # NOTE: SQLite supports ADD COLUMN but not DROP/ALTER existing.
        try:
            res = await conn.execute(text("PRAGMA table_info(blocks)"))
            existing_cols = {row[1] for row in res.fetchall()}  # row[1] = name

            # New columns added after initial scaffold.
            migrations = [
                ("source_image_path", "TEXT"),
                ("working_image_path", "TEXT"),
                ("current_detail", "TEXT"),
                # Reconstruction (OpenMVS) fields
                ("recon_status", "VARCHAR(32)"),
                ("recon_progress", "FLOAT"),
                ("recon_current_stage", "VARCHAR(100)"),
                ("recon_output_path", "TEXT"),
                ("recon_error_message", "TEXT"),
                ("recon_statistics", "JSON"),
                # 3D Gaussian Splatting (3DGS) fields
                ("gs_status", "VARCHAR(32)"),
                ("gs_progress", "FLOAT"),
                ("gs_current_stage", "VARCHAR(100)"),
                ("gs_output_path", "TEXT"),
                ("gs_error_message", "TEXT"),
                ("gs_statistics", "JSON"),
                # 3D Tiles Conversion fields
                ("tiles_status", "VARCHAR(32)"),
                ("tiles_progress", "FLOAT"),
                ("tiles_current_stage", "VARCHAR(100)"),
                ("tiles_output_path", "TEXT"),
                ("tiles_error_message", "TEXT"),
                ("tiles_statistics", "JSON"),
                # 3D GS Tiles Conversion fields
                ("gs_tiles_status", "VARCHAR(32)"),
                ("gs_tiles_progress", "FLOAT"),
                ("gs_tiles_current_stage", "VARCHAR(100)"),
                ("gs_tiles_output_path", "TEXT"),
                ("gs_tiles_error_message", "TEXT"),
                ("gs_tiles_statistics", "JSON"),
                # Partitioned SfM fields
                ("partition_enabled", "BOOLEAN"),
                ("partition_strategy", "VARCHAR(64)"),
                ("partition_params", "JSON"),
                ("sfm_pipeline_mode", "VARCHAR(64)"),
                ("merge_strategy", "VARCHAR(64)"),
                # GLOMAP-specific fields (mapper vs mapper_resume and versioning)
                ("glomap_mode", "VARCHAR(32)"),
                ("parent_block_id", "VARCHAR(36)"),
                ("input_colmap_path", "TEXT"),
                ("output_colmap_path", "TEXT"),
                ("version_index", "INTEGER"),
                ("glomap_params", "JSON"),
                # openMVG-specific parameters snapshot
                ("openmvg_params", "JSON"),
                # Task Queue fields
                ("queue_position", "INTEGER"),
                ("queued_at", "DATETIME"),
            ]

            for col, col_type in migrations:
                if col not in existing_cols:
                    await conn.execute(
                        text(f"ALTER TABLE blocks ADD COLUMN {col} {col_type}")
                    )
        except Exception:
            # If anything goes wrong, don't block startup; tests use fresh DB anyway.
            pass


async def get_db():
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
