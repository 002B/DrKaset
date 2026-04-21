# DrKaset — Backend

RAG-based agricultural assistant API for Thai farmers.
Stack: FastAPI · Ollama (Python lib) · FAISS · MySQL · JWT

---

## โครงสร้างไฟล์ที่สร้าง

```
drkaset/
├── .env                              ← environment variables
├── .gitignore
│
├── backend/
│   ├── main.py                       ← FastAPI entry point
│   ├── requirements.txt
│   │
│   ├── core/
│   │   ├── config.py                 ← pydantic-settings โหลด .env
│   │   ├── database.py               ← SQLAlchemy engine + get_db()
│   │   └── crop_constants.py         ← 14 พืช, region keywords, LLM config
│   │
│   ├── models/
│   │   ├── db_models.py              ← ORM: User, ChatSession, ChatMessage, IngestionLog
│   │   └── schemas.py                ← Pydantic request/response schemas
│   │
│   ├── rag/
│   │   ├── embedder.py               ← HuggingFaceEmbeddings singleton
│   │   ├── retriever.py              ← FAISS load + search พร้อม filter crop/region
│   │   ├── intent_detector.py        ← detect_intent / detect_crop / detect_region
│   │   └── prompt_builder.py         ← build_profit/compare/knowledge/fallback prompt
│   │
│   ├── services/
│   │   ├── rag_service.py            ← orchestrator → stream_response() async generator
│   │   ├── auth_service.py           ← hash/verify password, JWT create/verify
│   │   └── vector_store.py           ← FAISS load/save/merge helpers
│   │
│   ├── api/
│   │   ├── auth.py                   ← POST /auth/register, /login, /refresh
│   │   ├── chat.py                   ← POST /chat (SSE stream), GET /chat/sessions
│   │   ├── ingest.py                 ← POST /ingest/upload, GET /ingest/logs
│   │   └── health.py                 ← GET /health
│   │
│   └── data/
│       ├── faiss_index/              ← ★ วาง index.faiss + index.pkl ที่นี่ ★
│       ├── raw/                      ← ไฟล์ที่ upload ผ่าน API
│       └── processed/
│
└── db/
    ├── init.sql                      ← รันครั้งแรกเพื่อสร้าง schema ทั้งหมด
    └── migrations/
        ├── 001_users.sql
        ├── 002_chat.sql
        └── 003_ingestion_logs.sql
```

---

## วิธีติดตั้งและรัน

### 1. ติดตั้ง Ollama และ pull model

```bash
# ติดตั้ง Ollama จาก https://ollama.ai
ollama serve
ollama pull qwen2.5:7b
```

### 2. ตั้งค่า MySQL

รัน MAMP / XAMPP / brew services หรือ mysql.server start แล้ว:

```bash
mysql -u root -p < db/init.sql
```

script นี้จะ:
- สร้าง database `drkaset_db`
- สร้าง user `drkaset_user` / password `drkaset_pass`
- สร้าง tables ทั้งหมด (users, chat_sessions, chat_messages, ingestion_logs)

> **หมายเหตุ:** ถ้าใช้ MAMP password ของ root อาจเป็น `root`
> แก้ไข `.env` ให้ตรงกับ MySQL ที่ใช้

### 3. สร้าง virtual environment และติดตั้ง dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. ตั้งค่า .env

แก้ไขไฟล์ `.env` ที่ root ของ project:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=drkaset_user
MYSQL_PASSWORD=drkaset_pass
MYSQL_DATABASE=drkaset_db

JWT_SECRET_KEY=เปลี่ยนเป็น_secret_ของจริง
```

### 5. วาง FAISS index

หลังจากรัน data_preparation pipeline เสร็จแล้ว:

```bash
# copy ไฟล์ FAISS index มาวางที่ backend
cp -r data_preparation/data/faiss_index/index.faiss backend/data/faiss_index/
cp -r data_preparation/data/faiss_index/index.pkl   backend/data/faiss_index/
```

ไฟล์ที่ต้องมีใน `backend/data/faiss_index/`:
- `index.faiss`
- `index.pkl`

### 6. รัน Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

ตรวจสอบว่า API ทำงานได้:
```
GET http://localhost:8000/health
```

---

## API Endpoints

| Method | Path | คำอธิบาย |
|--------|------|----------|
| POST | /auth/register | สมัครสมาชิก |
| POST | /auth/login | เข้าสู่ระบบ → รับ JWT |
| POST | /auth/refresh | ต่ออายุ token |
| POST | /chat | ส่งข้อความ → SSE stream ตอบกลับ |
| GET | /chat/sessions | ดูประวัติ sessions |
| GET | /chat/sessions/{id}/messages | ดูข้อความใน session |
| POST | /ingest/upload | อัพโหลดไฟล์ข้อมูลไปยัง data/raw |
| GET | /ingest/logs | ดู log การอัพโหลด |
| GET | /health | ตรวจสอบสถานะ DB + Ollama + FAISS |

### ตัวอย่างการเรียก Chat API (SSE)

```javascript
const res = await fetch("http://localhost:8000/chat", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token}`,
  },
  body: JSON.stringify({ message: "ข้าวโพดปลูกยังไง" }),
});

const reader = res.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value);
  // parse SSE lines
  for (const line of text.split("\n")) {
    if (line.startsWith("data:")) {
      const data = JSON.parse(line.slice(5));
      if (data.token) process.stdout.write(data.token);
    }
  }
}
```

---

## การเพิ่ม FAISS Index ใหม่ (หลัง data_preparation)

เมื่อได้ชุดข้อมูลใหม่และรัน pipeline แล้ว แค่ copy ทับ:

```bash
cp data_preparation/data/faiss_index/index.faiss backend/data/faiss_index/
cp data_preparation/data/faiss_index/index.pkl   backend/data/faiss_index/
```

จากนั้น restart backend เพื่อโหลด index ใหม่:
```bash
# กด Ctrl+C แล้วรัน uvicorn ใหม่
uvicorn main:app --reload --port 8000
```

---

## หมายเหตุสำคัญ

- **Ollama ใช้ Python lib** (`import ollama`) ไม่ใช่ HTTP request ตรง
- **ไม่มี Celery / Redis / Docker** — ทุกอย่างรันใน process เดียว
- **ไม่มีการ fetch ราคา/อากาศจาก API ภายนอก** — ข้อมูลทั้งหมดมาจาก FAISS ที่สร้างจาก dataset ของคุณ
- **Tables สร้างอัตโนมัติ** ตอน startup ผ่าน `Base.metadata.create_all()` แต่แนะนำให้รัน `db/init.sql` ก่อนเพื่อสร้าง user และ database
