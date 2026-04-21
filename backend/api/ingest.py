from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
import shutil, os
from datetime import datetime

from core.database import get_db
from models.db_models import IngestionLog, User
from models.schemas import UploadResponse
from services.auth_service import verify_token

router = APIRouter(prefix="/ingest", tags=["ingest"])

UPLOAD_DIR = "./data/raw"
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".pdf", ".json", ".txt", ".zip"}


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


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    _get_current_user(authorization, db)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    dest = os.path.join(UPLOAD_DIR, file.filename)

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    log = IngestionLog(
        file_name=file.filename,
        file_type=ext,
        status="done",
        record_count=0,
        finished_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return UploadResponse(
        log_id=log.id,
        file_name=log.file_name,
        status=log.status,
        record_count=log.record_count,
    )


@router.get("/logs")
def ingest_logs(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
):
    _get_current_user(authorization, db)
    logs = db.query(IngestionLog).order_by(IngestionLog.created_at.desc()).limit(50).all()
    return [
        {
            "id": l.id, "file_name": l.file_name, "file_type": l.file_type,
            "status": l.status, "record_count": l.record_count,
            "created_at": l.created_at, "finished_at": l.finished_at,
        }
        for l in logs
    ]
