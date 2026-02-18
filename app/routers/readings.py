"""
Weight readings endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.schemas import WeightReadingCreate, WeightReadingResponse
from app.services.readings import process_reading

router = APIRouter()


@router.post("/readings", response_model=dict, status_code=201)
async def create_reading(
    reading: WeightReadingCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new weight reading
    
    This endpoint:
    1. Upserts the UID in tags table
    2. Stores reading in weight_readings
    3. Calculates net_weight = gross_weight - tare_weight
    4. Updates spool_state
    5. Optionally pushes to Spoolman if enabled
    """
    try:
        result = await process_reading(db, reading)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
