from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .config import settings
from .database import SessionLocal, init_db, get_history, save_message, Message
from .llm_service import generate_reply

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Lyftr AI Chatbot API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

async def get_db():
    async with SessionLocal() as db:
        yield db

class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)
    system_prompt: str | None = None

    @field_validator("session_id", "message")
    @classmethod
    def not_blank(cls, value: str):
        if not value.strip():
            raise ValueError("Field cannot be empty")
        return value.strip()

@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    if len(settings.llm_api_keys) < 2:
        raise HTTPException(status_code=503, detail="at least two API keys must be configured")
    try:
        await db.execute(select(Message.id).limit(1))
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {
        "status": "ok",
        "keys_configured": len(settings.llm_api_keys),
        "cache_enabled": True,
    }

@app.post("/chat")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    x_simulate_failure: str | None = Header(default=None, alias="X-Simulate-Failure"),
):
    if len(settings.llm_api_keys) < 2:
        raise HTTPException(status_code=503, detail="all providers unavailable")

    history = await get_history(db, request.session_id)
    system_prompt = request.system_prompt or settings.default_system_prompt
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend({"role": item["role"], "content": item["content"]} for item in history)
    messages.append({"role": "user", "content": request.message})

    try:
        reply, metadata = await generate_reply(messages, x_simulate_failure)
    except RuntimeError as exc:
        if str(exc) == "all providers unavailable":
            raise HTTPException(status_code=503, detail="all providers unavailable")
        raise HTTPException(status_code=503, detail="all providers unavailable")
    except Exception:
        raise HTTPException(status_code=503, detail="all providers unavailable")

    # Persist only after successful inference. Failed requests never enter history.
    await save_message(db, request.session_id, "user", request.message)
    await save_message(db, request.session_id, "assistant", reply, metadata)
    return {"session_id": request.session_id, "reply": reply, "metadata": metadata}

@app.get("/sessions/{session_id}/messages")
async def session_messages(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Message.id).where(Message.session_id == session_id).limit(1))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {"session_id": session_id, "messages": await get_history(db, session_id)}
