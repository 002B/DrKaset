from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import engine
from models.db_models import Base
from rag.retriever import load_faiss

from api.auth import router as auth_router
from api.chat import router as chat_router
from api.ingest import router as ingest_router
from api.health import router as health_router

# ── App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="DrKaset API",
    version="1.0.0",
    description="Agricultural assistant RAG API for Thai farmers",
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(ingest_router)
app.include_router(health_router)


# ── Startup / Shutdown ────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)
    print("[DB] Tables ensured.")

    # Load FAISS index
    load_faiss()
    print("[Startup] Done.")


@app.on_event("shutdown")
def shutdown():
    print("[Shutdown] Bye.")


@app.get("/")
def root():
    return {"message": "DrKaset API is running"}
