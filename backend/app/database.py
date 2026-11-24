from contextlib import asynccontextmanager
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column
import json
from datetime import datetime, timezone
from .config import settings

def _normalize_url(url: str) -> str:
    # The assignment's sqlite:////data/app.db form is supported.
    if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url

DATABASE_URL = _normalize_url(settings.database_url)
if DATABASE_URL.startswith("sqlite+aiosqlite:///") and "/data/" in DATABASE_URL:
    Path("/data").mkdir(parents=True, exist_ok=True)

engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_history(db: AsyncSession, session_id: str) -> list[dict]:
    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.id.asc())
    )
    rows = result.scalars().all()
    history = []
    for row in rows:
        item = {"role": row.role, "content": row.content}
        if row.role == "assistant" and row.metadata_json:
            item["metadata"] = json.loads(row.metadata_json)
        history.append(item)
    return history

async def save_message(db: AsyncSession, session_id: str, role: str, content: str, metadata: dict | None = None):
    row = Message(
        session_id=session_id,
        role=role,
        content=content,
        metadata_json=json.dumps(metadata) if metadata is not None else None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(row)
    await db.commit()
    return row
