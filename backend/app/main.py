from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api.v1 import user, plan, history, reminders, chat
from app.core.rag.knowledge_base import init_knowledge_base, get_knowledge_stats
from app.core.reminder.scheduler import init_scheduler, shutdown_scheduler, get_registered_job_count

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: RAG knowledge base
    init_knowledge_base()
    stats = get_knowledge_stats()
    print(f"[FitAgent] Knowledge base: {stats['document_count']} documents indexed")

    # Startup: APScheduler reminder runtime (Phase 2C)
    scheduler_ok = await init_scheduler()
    if scheduler_ok:
        print(f"[FitAgent] Reminder scheduler: running ({get_registered_job_count()} jobs restored)")
    else:
        print("[FitAgent] Reminder scheduler: degraded (system will run without scheduled reminders)")

    yield

    # Shutdown
    await shutdown_scheduler()


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(user.router, prefix="/api/v1")
app.include_router(plan.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(reminders.router, prefix="/api/v1")  # Phase 2C


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "scheduler": "running" if get_registered_job_count() >= 0 else "degraded",
    }


@app.get("/rag/stats")
async def rag_stats():
    """Return knowledge base statistics."""
    return get_knowledge_stats()
