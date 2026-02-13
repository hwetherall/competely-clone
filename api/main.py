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

from api.routes import runs_router, variables_router

# Create FastAPI app
app = FastAPI(
    title="CompetelyClone API",
    description="API for AI-powered competitive analysis",
    version="1.0.0",
)

# CORS: allow frontend origin(s). In production set CORS_ORIGINS (comma-separated).
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").strip()
allow_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
