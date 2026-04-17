"""Pydantic request/response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AddRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class AddResponse(BaseModel):
    ok: bool = True
    memories: list[dict[str, Any]]

class ExplainResponse(BaseModel):
    ok: bool = True
    explanations: list[dict[str, Any]]


class ChatResponse(BaseModel):
    ok: bool = True
    reply: str


class ErrorResponse(BaseModel):
    ok: bool = False
    detail: str
    code: str | None = None

