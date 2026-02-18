"""
Sync endpoints for Spoolman integration
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import SyncResponse, OpenSpoolWriteResponse
from app.services.sync import pull_from_spoolman, push_to_spoolman
from app.services.openspool import write_openspool_tag
from app.config import settings

router = APIRouter()


@router.post("/spoolman/pull", response_model=SyncResponse)
async def sync_pull_spoolman(db: Session = Depends(get_db)):
    """
    Pull spool metadata from Spoolman
    
    Fetches metadata for all mapped spools and updates the local cache
    """
    if not settings.spoolman_url:
        raise HTTPException(
            status_code=400,
            detail="Spoolman URL not configured"
        )
    
    try:
        result = await pull_from_spoolman(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spoolman/push/{uid}", response_model=SyncResponse)
async def sync_push_spoolman(uid: str, db: Session = Depends(get_db)):
    """
    Push spool weight to Spoolman
    
    Updates the remaining weight in Spoolman for a specific spool
    """
    if not settings.spoolman_url:
        raise HTTPException(
            status_code=400,
            detail="Spoolman URL not configured"
        )
    
    try:
        result = await push_to_spoolman(db, uid)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tags/{uid}/write_openspool", response_model=OpenSpoolWriteResponse)
async def write_openspool(
    uid: str,
    force: bool = False,
    db: Session = Depends(get_db)
):
    """
    Write OpenSpool data to NFC tag
    
    This endpoint is intentionally restricted and requires WRITE_MODE=true
    unless force is specified (for manual administrative use)
    """
    if not settings.write_mode and not force:
        raise HTTPException(
            status_code=403,
            detail="Write mode is disabled. Set WRITE_MODE=true or use force parameter"
        )
    
    try:
        result = await write_openspool_tag(db, uid)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
