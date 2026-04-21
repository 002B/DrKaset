from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ---- Auth ----
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---- Chat ----
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None


class ChatResponse(BaseModel):
    session_id: int
    message_id: int
    intent: Optional[str] = None
    # actual content is streamed via SSE


# ---- Ingest ----
class UploadResponse(BaseModel):
    log_id: int
    file_name: str
    status: str
    record_count: int


# ---- Health ----
class HealthResponse(BaseModel):
    db: str
    ollama: str
    faiss: str


# ---- Session / Message ----
class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    intent: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    id: int
    title: Optional[str]
    created_at: datetime
    messages: List[MessageOut] = []

    class Config:
        from_attributes = True
