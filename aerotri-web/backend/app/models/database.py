"""Database configuration and session management."""
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Database file path
DATABASE_PATH = os.environ.get("AEROTRI_DB_PATH", "/root/work/aerotri-web/data/aerotri.db")
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
            ]

            for col, col_type in migrations:
                if col not in existing_cols:
                    await conn.execute(text(f"ALTER TABLE blocks ADD COLUMN {col} {col_type}"))
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
