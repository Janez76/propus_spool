"""
Main FastAPI application for propus_spool
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.routers import readings, tags, sync, health

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting propus_spool application")
    logger.info(f"Database URL: {settings.database_url}")
    logger.info(f"Spoolman URL: {settings.spoolman_url}")
    logger.info(f"Write Mode: {settings.write_mode}")
    logger.info(f"Push to Spoolman: {settings.push_remaining_to_spoolman}")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down propus_spool application")


# Create FastAPI app
app = FastAPI(
    title="Propus Spool",
    description="Modular filament scale and NFC UID management system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(readings.router, prefix="/api/v1", tags=["readings"])
app.include_router(tags.router, prefix="/api/v1", tags=["tags"])
app.include_router(sync.router, prefix="/api/v1/sync", tags=["sync"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Propus Spool",
        "version": "1.0.0",
        "description": "Modular filament scale and NFC UID management system"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
