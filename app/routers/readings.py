"""API router for weight readings."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import ReadingCreate, ReadingResponse
from app.services.reading import ReadingService
from app.clients.spoolman import get_spoolman_client, SpoolmanClient

router = APIRouter(prefix="/readings", tags=["readings"])


@router.post("/", response_model=ReadingResponse)
async def create_reading(
    reading: ReadingCreate,
    db: Session = Depends(get_db),
    spoolman_client: SpoolmanClient = Depends(get_spoolman_client)
):
    """
    Process a weight reading from a scale device.
    
    This endpoint:
    - Upserts the UID in the tags table
    - Stores the reading in history
    - Calculates net_weight = gross_weight - tare_weight
    - Updates spool_state
    - Optionally pushes to Spoolman if enabled
    """
    service = ReadingService(db, spoolman_client)
    result = await service.process_reading(
        device_id=reading.device_id,
        uid=reading.uid,
        gross_weight_g=reading.gross_weight_g,
        timestamp=reading.timestamp
    )
    
    return ReadingResponse(**result)
