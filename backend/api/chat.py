from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import json

from core.database import get_db
from models.db_models import User, ChatSession, ChatMessage
from models.schemas import ChatRequest
from services.rag_service import stream_response, get_intent
from services.auth_service import verify_token

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_current_user(authorization: Optional[str], db: Session) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("")
async def chat(
    payload: ChatRequest,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _get_current_user(authorization, db)

    # Get or create session
    if payload.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == payload.session_id,
            ChatSession.user_id == user.id,
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(
            user_id=user.id,
            title=payload.message[:50],
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=payload.message,
    )
    db.add(user_msg)
    db.commit()

    intent = get_intent(payload.message)

    # Buffer assistant reply for saving after stream
    collected: list[str] = []

    async def event_generator():
        # Send metadata first
        meta = json.dumps({"session_id": session.id, "intent": intent})
        yield f"event: meta\ndata: {meta}\n\n"

        async for token in stream_response(payload.message):
            collected.append(token)
            yield f"data: {json.dumps({'token': token})}\n\n"

        # Save assistant message after stream ends
        full_reply = "".join(collected)
        assistant_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=full_reply,
            intent=intent,
        )
        db.add(assistant_msg)
        db.commit()

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sessions")
def list_sessions(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _get_current_user(authorization, db)
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [{"id": s.id, "title": s.title, "created_at": s.created_at} for s in sessions]


@router.get("/sessions/{session_id}/messages")
def get_messages(
    session_id: int,
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _get_current_user(authorization, db)
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        {"id": m.id, "role": m.role, "content": m.content,
         "intent": m.intent, "created_at": m.created_at}
        for m in messages
    ]
