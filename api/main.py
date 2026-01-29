"""
FastAPI application for CompetelyClone API.

Run with:
    uvicorn api.main:app --reload --port 8000

Or from the api directory:
    uvicorn main:app --reload --port 8000
"""

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

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(runs_router, prefix="/api/runs", tags=["runs"])
app.include_router(variables_router, prefix="/api/variables", tags=["variables"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "competelyclone-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
