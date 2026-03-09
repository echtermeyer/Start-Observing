import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from app.api.routes import router
from app.storage.json_store import init_default_data


def check_api_key():
    """Check if Anthropic API key is configured."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        print("\n" + "="*60)
        print("WARNING: ANTHROPIC_API_KEY not configured!")
        print("AI features will not work without a valid API key.")
        print("To configure:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your Anthropic API key")
        print("="*60 + "\n")
        return False
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize default data and check configuration
    init_default_data()
    app.state.ai_enabled = check_api_key()
    yield
    # Shutdown: nothing to do


app = FastAPI(
    title="Agentic Dashboard API",
    description="Backend API for AI-powered data visualization and analysis",
    version="0.2.0",
    lifespan=lifespan
)

cors_origins = ["http://localhost:5173", "http://localhost:3000", "http://localhost:3001"]
if os.environ.get("FRONTEND_URL"):
    cors_origins.append(os.environ["FRONTEND_URL"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
def health_check():
    """Check API health and AI availability."""
    ai_enabled = getattr(app.state, 'ai_enabled', False)
    return {
        "status": "healthy",
        "ai_enabled": ai_enabled,
        "version": "0.2.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
