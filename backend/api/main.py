from __future__ import annotations

"""
DocMind Second Brain — Main FastAPI Application
Entry point for REST API server with CORS, health monitoring, and modular routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.database.connection import init_db
from backend.api.v1.documents import router as documents_router
from backend.api.v1.retrieval import router as retrieval_router
from backend.api.v1.chat import router as chat_router
from backend.api.v1.memory import router as memory_router
from backend.api.v1.knowledge import router as knowledge_router
from backend.api.v1.outputs import router as outputs_router
from core.llm import get_model_info


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown events."""
    print("[DocMind API] Starting Second Brain services...")
    init_db()
    yield
    print("[DocMind API] Shutting down Second Brain services.")


app = FastAPI(
    title="DocMind RAG + Second Brain API",
    description="Persistent Knowledge, Context, Selective Memory, and Document Intelligence API.",
    version="2.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount v1 routers
app.include_router(documents_router, prefix="/api/v1")
app.include_router(retrieval_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(memory_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(outputs_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
def health_check():
    """System health check and LLM readiness telemetry."""
    model_info = get_model_info()
    return {
        "status": "healthy",
        "system": "DocMind RAG + Second Brain",
        "version": "2.0.0",
        "llm_ready": model_info.get("is_ready", False),
        "active_model": model_info.get("model_name", "None"),
        "gpu_layers": model_info.get("n_gpu_layers", 0),
        "available_models": model_info.get("available_models", []),
    }


from pydantic import BaseModel, ConfigDict
from core.llm import set_active_model


class SwitchModelRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_name: str


@app.get("/api/v1/models", tags=["System"])
def list_models_endpoint():
    """Lists available local GGUF models and current active model."""
    info = get_model_info()
    info["active_model"] = info.get("model_name", "None")
    return info


@app.post("/api/v1/models/switch", tags=["System"])
def switch_model_endpoint(req: SwitchModelRequest):
    """Dynamically switches active local LLM model without restarting server."""
    success = set_active_model(req.model_name)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Model '{req.model_name}' not found in models/ directory.")
    return {"success": True, "active_model": req.model_name}


from pathlib import Path
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

# Resolve frontend distribution directory
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
    # Mount /assets if it exists
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Exclude API, health, and docs from SPA fallback
        if full_path.startswith("api/") or full_path in ("health", "docs", "redoc", "openapi.json"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Endpoint not found")

        target_file = FRONTEND_DIST / full_path
        if full_path and target_file.is_file():
            return FileResponse(target_file)

        return FileResponse(FRONTEND_DIST / "index.html")
else:
    @app.get("/", tags=["System"])
    def root():
        """Root info endpoint when frontend is not yet built."""
        return {
            "message": "Welcome to DocMind RAG + Second Brain API",
            "docs_url": "/docs",
            "health_url": "/health",
            "frontend_status": "Build pending. Run 'npm run build' inside frontend/ to serve the React UI on port 8000.",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.main:app", host="127.0.0.1", port=8000, reload=True)
