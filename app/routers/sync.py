"""API router for Spoolman synchronization."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import SpoolmanSyncResponse
from app.services.spoolman_sync import SpoolmanSyncService
from app.clients.spoolman import get_spoolman_client, SpoolmanClient

router = APIRouter(prefix="/sync/spoolman", tags=["sync"])


@router.post("/pull", response_model=SpoolmanSyncResponse)
async def pull_from_spoolman(
    db: Session = Depends(get_db),
    spoolman_client: SpoolmanClient = Depends(get_spoolman_client)
):
    """
    Pull spool metadata from Spoolman and cache it locally.
    
    This syncs filament information (brand, material, color, temps, etc.)
    from Spoolman to the local cache.
    """
    service = SpoolmanSyncService(db, spoolman_client)
    result = await service.pull_metadata()
    return SpoolmanSyncResponse(**result)


@router.post("/push/{uid}")
async def push_to_spoolman(
    uid: str,
    db: Session = Depends(get_db),
    spoolman_client: SpoolmanClient = Depends(get_spoolman_client)
):
    """
    Manually push current weight of a specific tag to Spoolman.
    
    This updates the remaining_weight field in Spoolman for the
    spool associated with this tag.
    """
    service = SpoolmanSyncService(db, spoolman_client)
    success = await service.push_weight(uid)
    
    if success:
        return {"success": True, "message": f"Successfully pushed weight for tag {uid} to Spoolman"}
    else:
        return {"success": False, "message": f"Failed to push weight for tag {uid}. Check if tag is assigned to a spool."}
