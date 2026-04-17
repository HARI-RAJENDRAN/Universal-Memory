"""FastAPI application: multi-user memory + Ollama chat."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from unimem.api.schemas import AddRequest, AddResponse, ChatRequest, ChatResponse
from unimem.core.memory_client import MemoryClient
from unimem.db.bootstrap import create_all_tables, ensure_pgvector_extension
from unimem.db.session import get_db, init_engine
from unimem.services.memory_service import MemoryService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("unimem.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB engine and schema on startup."""
    init_engine()
    ensure_pgvector_extension()
    create_all_tables()
    logger.info("API startup complete")
    yield


app = FastAPI(
    title="unimem",
    description="Multi-user memory API (PostgreSQL + pgvector + Ollama)",
    version="0.2.0",
    lifespan=lifespan,
)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.exception("Database error")
    return JSONResponse(
        status_code=503,
        content={
            "ok": False,
            "detail": "A database error occurred. Check PostgreSQL availability and migrations.",
            "code": "database_error",
        },
    )


@app.post("/add", response_model=AddResponse)
def add_memory(body: AddRequest, db: Session = Depends(get_db)):
    """Persist extracted memory for a user (with vector deduplication)."""
    service = MemoryService(db)
    try:
        memories = service.add_memory(user_id=body.user_id, text=body.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AddResponse(memories=memories)


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, db: Session = Depends(get_db)):
    """Retrieve ranked memories and generate a reply with the local LLM."""
    client = MemoryClient(db)
    try:
        reply = client.chat(query=body.message, user_id=body.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ChatResponse(reply=reply)


@app.get("/memory/{user_id}")
def list_memory(user_id: str, db: Session = Depends(get_db)):
    """List stored memories for one user (metadata only, no embeddings)."""
    service = MemoryService(db)
    if not user_id.strip():
        raise HTTPException(status_code=400, detail="user_id must not be empty")
    try:
        rows = service.list_user_memories(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "user_id": user_id, "memories": rows}

