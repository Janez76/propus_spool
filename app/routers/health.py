"""
Health check endpoint
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import HealthResponse
from app.config import settings
import httpx

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint
    
    Returns status of the application, database, and external services
    """
    # Check database
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check Spoolman if configured
    spoolman_status = None
    if settings.spoolman_url:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.spoolman_url}/health",
                    timeout=5.0
                )
                spoolman_status = "ok" if response.status_code == 200 else f"status: {response.status_code}"
        except Exception as e:
            spoolman_status = f"error: {str(e)}"
    
    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        database=db_status,
        spoolman=spoolman_status
    )
