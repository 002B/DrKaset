# DrKaset — Full Project Structure (No Docker / No Celery / No Redis)

## Stack Overview
| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite + **JavaScript** |
| Backend | Python 3.11 + FastAPI |
| LLM | Ollama local — `qwen2.5:7b` (temperature=0.2) |
| Embeddings | `BAAI/bge-small-en-v1.5` (normalize=True) |
| Vector Store | FAISS (chunk_size=900, overlap=150) |
| Database | MySQL 9.4 |
| Scheduler | **APScheduler** (รันใน FastAPI process เดียวกัน) |

> ไม่ใช้ Docker, Celery, Redis — รัน service แต่ละตัวโดยตรงบนเครื่อง

---

## วิธีรัน (ลดจาก 7 commands เหลือ 5)

```bash
# 1. Ollama
ollama serve
ollama pull qwen2.5:7b

# 2. MySQL — รันผ่าน MAMP / XAMPP / brew services / mysql.server start

# 3. Backend (FastAPI)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 4. Frontend
cd frontend
npm install
npm run dev
```

---

```
drkaset/
│
├── .env                               # environment variables (ไม่มี Docker — ใช้ localhost ทุกตัว)
├── .gitignore
└── README.md
│
│
├── frontend/                          # React 18 + Vite + JavaScript
│   ├── public/
│   │   └── favicon.ico
│   ├── src/
│   │   ├── components/
│   │   │   ├── LoginPage.jsx          # หน้า Login รับ email/password → POST /auth/login → เก็บ JWT ใน memory
│   │   │   ├── RegisterPage.jsx       # หน้าสมัครสมาชิก → POST /auth/register
│   │   │   ├── ChatWindow.jsx         # หน้าแชทหลัก แสดง conversation + ประวัติ + SSE streaming
│   │   │   ├── MessageBubble.jsx      # render message แต่ละอัน รองรับ markdown + badge intent
│   │   │   ├── InputBar.jsx           # input box + send button + suggestion chips
│   │   │   └── StatusBar.jsx          # แสดงสถานะ model ready / loading
│   │   ├── hooks/
│   │   │   ├── useChat.js             # SSE stream hook: loading state, error, append token
│   │   │   └── useAuth.js             # JWT hook: login / logout / refresh token
│   │   ├── services/
│   │   │   └── api.js                 # axios client: base URL, Authorization header interceptor
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
│
├── backend/                           # FastAPI + Python 3.11
│   ├── main.py                        # entry point: register routers, CORS, startup
│   │                                  # → โหลด FAISS + Ollama check + เริ่ม APScheduler
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── chat.py                    # POST /chat → enforce_query_scope → detect_intent → rag_service → SSE stream
│   │   ├── auth.py                    # POST /auth/login, /auth/register, /auth/refresh → ออก JWT
│   │   ├── ingest.py                  # POST /ingest/upload (multipart) → loader → pipeline → FAISS upsert
│   │   └── health.py                  # GET /health → check DB + Ollama + FAISS loaded
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── rag_service.py             # orchestrator: detect_intent → retriever → prompt_builder → llm.invoke → stream
│   │   ├── vector_store.py            # FAISS.load_local / save_local / search / merge_from (incremental)
│   │   ├── structured_data.py         # profit_table, _get_snapshot_safe(), PROFIT_LOOKUP_TABLE จาก MySQL
│   │   ├── auth_service.py            # hash_password, verify_password, create_access_token, verify_token
│   │
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── embedder.py                # HuggingFaceEmbeddings singleton (BAAI/bge-small-en-v1.5, device=cpu, normalize=True)
│   │   ├── retriever.py               # embed query → FAISS top-k search พร้อม filter crop/region
│   │   ├── prompt_builder.py          # build_profit_prompt / build_compare_prompt / build_knowledge_prompt / build_fallback_prompt
│   │   └── intent_detector.py         # detect_intent(), detect_crop(), detect_crop_in_text(), detect_region_from_text()
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── loader.py                  # auto-detect file type → เรียก parser ที่เหมาะสม (csv/xlsx/pdf/json/txt/zip)
│   │   ├── processor.py               # normalize_record_from_row(), build_record_text(), clean_text(), to_number()
│   │   ├── hf_loader.py               # load bmazahiro/thai-planting-dataset-1000-items → filter 14 crops → embed
│   │   └── embedder_pipeline.py       # records → chunk → embed → save FAISS
│   │                                  
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── db_models.py               # SQLAlchemy ORM: User, ChatSession, ChatMessage, CropPrice, WeatherData, IngestionLog
│   │   └── schemas.py                 # Pydantic: ChatRequest, ChatResponse, LoginRequest, TokenResponse, UploadResponse
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                  # pydantic-settings: โหลด .env → Settings object
│   │   ├── database.py                # SQLAlchemy engine + SessionLocal + get_db() dependency
│   │   └── crop_constants.py          # TARGET_CROPS (14 พืช + aliases), REGION_KEYWORDS, NON_SCOPE_CROP_HINTS
│   │
│   ├── data/
│   │   ├── faiss_index/               # FAISS index โหลดตอน startup (copy มาจาก data_preparation)
│   │   ├── raw/                       # ไฟล์ที่ upload ผ่าน API
│   │   └── processed/                 # records หลัง normalize
│   │
│   └── requirements.txt
│
│
├── db/                                # MySQL 8 schema
│   ├── init.sql                       # รันครั้งแรกเพื่อสร้าง schema ทั้งหมด
│   └── migrations/
│       ├── 001_users.sql              # table users: id, email, hashed_password, created_at
│       ├── 002_chat.sql               # table chat_sessions + chat_messages
│
│       
│       
│       
│
│
└── data_preparation/                  # ETL + RAG pipeline (รันแยก ก่อน start backend)
    │
    ├── data/                          # ★ โยนไฟล์ชุดข้อมูลตรงนี้เลย ★
    │   ├── raw/                       # ← วางไฟล์ .xlsx .pdf .csv .json .txt .zip ได้เลย
    │   ├── processed/                 # cleaned records (auto-generate)
    │   └── faiss_index/               # vector store output (auto-generate)
    │                                  # → copy โฟลเดอร์นี้ไปวางที่ backend/data/faiss_index/
    │
    ├── ingest/
    │   ├── __init__.py
    │   ├── loader.py                  # dynamic loader: auto-detect ชนิดไฟล์
    │   │                              #   CSV/XLSX: try encodings utf-8, utf-8-sig, cp874, tis-620, latin1
    │   │                              #   PDF: pypdf page-by-page
    │   │                              #   ZIP: extract_zip_recursive() รองรับ nested zip
    │   ├── scraper.py                 # BeautifulSoup: check robots.txt, rate limit, tenacity retry
    │   └── api_fetcher.py             # OpenWeatherMap / FAO FAOSTAT / OAE / HuggingFace datasets
    │
    ├── cleansing/
    │   ├── __init__.py
    │   ├── cleaner.py                 # clean_text(): \u00a0, zero-width chars, whitespace, line endings
    │   ├── normalizer.py              # normalize_record_from_row(): column alias map, หน่วย, crop key
    │   └── validator.py               # is_record_in_scope(): กรองเฉพาะ 14 พืช, validate fields
    │
    ├── eda/
    │   ├── explore.ipynb              # distribution, missing values, outliers, crop count
    │   └── visualize.ipynb            # plot ราคาพืชรายเดือน, correlation crop × region
    │
    ├── rag_pipeline/
    │   ├── __init__.py
    │   ├── chunker.py                 # RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)
    │   │                              # ใส่ metadata ทุก chunk: {crop, region, source_type, file_name}
    │   ├── embedder.py                # HuggingFaceEmbeddings(BAAI/bge-small-en-v1.5, device=cpu, normalize=True)
    │   └── indexer.py                 # build_faiss_index() / save_faiss_index() / incremental merge_from()
    │
    ├── run_pipeline.py                # CLI:
    │                                  #   python run_pipeline.py --step all
    │                                  #   python run_pipeline.py --step ingest
    │                                  #   python run_pipeline.py --step clean
    │                                  #   python run_pipeline.py --step embed
    └── config.yaml                    # กำหนด paths, chunk_size, model, sources
```

---

## APScheduler ใน main.py

```python
from apscheduler.schedulers.background import BackgroundScheduler
from services.scheduler_service import fetch_weather, fetch_prices, fetch_soil

scheduler = BackgroundScheduler()

@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(fetch_weather, 'interval', hours=6)
    scheduler.add_job(fetch_prices,  'interval', days=1)
    scheduler.add_job(fetch_soil,    'interval', weeks=1)
    scheduler.start()

@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown()
```

---

## Model Config

```python
# LLM (backend/core/crop_constants.py)
OLLAMA_MODEL   = "qwen2.5:7b"
TEMPERATURE    = 0.2

# Embeddings
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
NORMALIZE       = True

# RAG
CHUNK_SIZE      = 900
CHUNK_OVERLAP   = 150
TOP_K           = 8    # profit / knowledge
TOP_K_COMPARE   = 10   # compare intent
```

---

## Data Flow

```
data_preparation/data/raw/      ← โยนไฟล์ xlsx / pdf / csv ตรงนี้
        ↓  python run_pipeline.py --step ingest
data_preparation/data/processed/
        ↓  python run_pipeline.py --step clean
cleaned + normalized records
        ↓  python run_pipeline.py --step embed
data_preparation/data/faiss_index/
        ↓  copy ไปวางที่
backend/data/faiss_index/       ← backend โหลดตอน startup
        ↓
Ollama qwen2.5:7b ตอบ user
```

---

## Environment Variables (.env)

```env
# LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# Embeddings
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

# FAISS
FAISS_INDEX_PATH=./data/faiss_index

# MySQL (local)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=drkaset_user
MYSQL_PASSWORD=drkaset_pass
MYSQL_DATABASE=drkaset_db

# JWT
JWT_SECRET_KEY=change_me_in_production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# External APIs
OPENWEATHER_API_KEY=your_key
OAE_BASE_URL=https://www.oae.go.th
FAO_BASE_URL=https://www.fao.org/faostat/en/api
HF_DATASET_NAME=bmazahiro/thai-planting-dataset-1000-items

# Scraping
SCRAPE_RATE_LIMIT_DELAY=2.0
SCRAPE_MAX_RETRIES=3

# CORS
ALLOWED_ORIGINS=http://localhost:5173
```

---
