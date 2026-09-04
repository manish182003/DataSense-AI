"""
DataSense FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routes import datasets, profile, ask, context, eval, ask_stream

app = FastAPI(
    title=settings.APP_NAME,
    description="Production-Grade Tabular Data-to-Insight Platform (DuckDB + Groq LLM + Plotly)",
    version="1.0.0"
)

# Enable CORS for React frontend (Vite default port 5173 & Vercel production URL)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(datasets.router)
app.include_router(profile.router)
app.include_router(ask.router)
app.include_router(context.router)
app.include_router(eval.router)
app.include_router(ask_stream.router)

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}

@app.get("/", tags=["System"])
async def root():
    return {
        "message": "Welcome to DataSense API",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
