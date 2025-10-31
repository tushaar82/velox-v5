"""
Database configuration and session management.
Provides SQLAlchemy setup for PostgreSQL and TimescaleDB.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData


# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}


class Base(DeclarativeBase):
    """Base class for all database models."""
    metadata = MetaData(naming_convention=convention)


class TimescaleBase(DeclarativeBase):
    """Base class for TimescaleDB time-series models."""
    metadata = MetaData(naming_convention=convention)


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(
        self,
        postgres_url: str,
        timescale_url: str,
        echo: bool = False
    ) -> None:
        """
        Initialize database manager.

        Args:
            postgres_url: PostgreSQL connection URL
            timescale_url: TimescaleDB connection URL
            echo: Whether to echo SQL statements
        """
        # PostgreSQL engine for relational data
        self.postgres_engine = create_async_engine(
            postgres_url,
            echo=echo,
            pool_size=20,
            max_overflow=40,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        # TimescaleDB engine for time-series data
        self.timescale_engine = create_async_engine(
            timescale_url,
            echo=echo,
            pool_size=20,
            max_overflow=40,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        # Session makers
        self.postgres_session_maker = async_sessionmaker(
            self.postgres_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        self.timescale_session_maker = async_sessionmaker(
            self.timescale_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    async def get_postgres_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get PostgreSQL session."""
        async with self.postgres_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def get_timescale_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get TimescaleDB session."""
        async with self.timescale_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_tables(self) -> None:
        """Create all database tables."""
        async with self.postgres_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with self.timescale_engine.begin() as conn:
            await conn.run_sync(TimescaleBase.metadata.create_all)

    async def close(self) -> None:
        """Close all database connections."""
        await self.postgres_engine.dispose()
        await self.timescale_engine.dispose()


# Global database manager instance (to be initialized in main.py)
db_manager: DatabaseManager | None = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting PostgreSQL session."""
    if db_manager is None:
        raise RuntimeError("Database manager not initialized")
    async for session in db_manager.get_postgres_session():
        yield session


async def get_timescale_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting TimescaleDB session."""
    if db_manager is None:
        raise RuntimeError("Database manager not initialized")
    async for session in db_manager.get_timescale_session():
        yield session
