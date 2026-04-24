"""
FastAPI application for CompetelyClone API.

Run with:
    uvicorn api.main:app --reload --port 8000

Or from the api directory:
    uvicorn main:app --reload --port 8000
"""

import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import runs_router, variables_router, plans_router, chat_router, discovery_router

# Create FastAPI app
app = FastAPI(
    title="CompetelyClone API",
    description="API for AI-powered competitive analysis",
    version="1.0.0",
)

# CORS: allow frontend origin(s). In production set CORS_ORIGINS (comma-separated).
# Normalize: no trailing slash (browser sends origin without slash).
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,null").strip()
allow_origins = [o.strip().rstrip("/") for o in _cors_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(runs_router, prefix="/api/runs", tags=["runs"])
app.include_router(variables_router, prefix="/api/variables", tags=["variables"])
app.include_router(plans_router, prefix="/api/plans", tags=["plans"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(discovery_router, prefix="/api/discovery", tags=["discovery"])


@app.get("/")
async def root():
    """Root: point to health and API docs."""
    return {
        "service": "CompetelyClone API",
        "health": "/api/health",
        "docs": "/docs",
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "competelyclone-api"}


@app.get("/api/debug/test-llm")
async def test_llm():
    """Test LLM connectivity for all configured models (with short timeouts)."""
    import asyncio
    from agents.llm_client import LLMClient, LLMError
    from config import settings

    models_to_test = {
        "plan_research": settings.PLAN_RESEARCH_MODEL,
        "plan_research_fallback": settings.PLAN_RESEARCH_FALLBACK_MODEL,
        "plan_fast": settings.PLAN_FAST_MODEL,
    }
    results = {}
    client = LLMClient()

    async def test_one(label: str, model: str):
        try:
            resp = await asyncio.wait_for(
                client.complete_simple(
                    prompt="Reply with exactly: OK",
                    system_prompt="You are a test bot. Reply with exactly one word.",
                    temperature=0,
                    max_tokens=10,
                    model_override=model,
                ),
                timeout=30,
            )
            return label, {"model": model, "status": "ok", "response": resp[:50]}
        except asyncio.TimeoutError:
            return label, {"model": model, "status": "timeout", "error": "No response within 30s"}
        except LLMError as e:
            return label, {"model": model, "status": "error", "error": e.message}
        except Exception as e:
            return label, {"model": model, "status": "error", "error": str(e)}

    tasks = [test_one(label, model) for label, model in models_to_test.items()]
    for label, result in await asyncio.gather(*tasks):
        results[label] = result

    return {
        "openrouter_key_set": bool(settings.OPENROUTER_API_KEY),
        "openrouter_key_prefix": settings.OPENROUTER_API_KEY[:12] + "..." if settings.OPENROUTER_API_KEY else None,
        "results": results,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
