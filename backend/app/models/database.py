from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from app.config import get_settings
import ssl

settings = get_settings()

# Serverless deployments (Vercel) need NullPool — no persistent connection pool
# across function invocations. Docker/long-running use a standard pool.
#
# Managed Postgres (Neon, Supabase, RDS) needs:
#   - ssl=require (TLS to the DB)
#   - statement_cache_size=0 when using PgBouncer transaction-mode pooler
if settings.serverless_mode or settings.database_ssl_require:
    _ssl_ctx = ssl.create_default_context()
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
        connect_args={"ssl": _ssl_ctx, "statement_cache_size": 0},
    )
else:
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


# ── Lazy one-time DB init (serverless: tables may not exist yet) ───────────────
_db_initialized = False


async def init_db():
    global _db_initialized
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _db_initialized = True


async def get_db() -> AsyncSession:  # type: ignore[override]
    if not _db_initialized:
        await init_db()
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
