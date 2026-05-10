from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import ensure_runtime_dirs, settings
from .routers import feedback, graph, integration, outlines, rag, report, textbooks


ensure_runtime_dirs()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "textbook_dir": str(settings.textbook_dir)}


app.include_router(textbooks.router)
app.include_router(outlines.router)
app.include_router(graph.router)
app.include_router(integration.router)
app.include_router(rag.router)
app.include_router(feedback.router)
app.include_router(report.router)
