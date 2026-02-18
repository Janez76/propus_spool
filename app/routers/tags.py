"""API router for tag operations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    TagResponse, 
    TagListResponse, 
    AssignSpoolRequest, 
    TareRequest,
    OpenSpoolWriteRequest,
    OpenSpoolWriteResponse
)
from app.models import Tag, SpoolState, SpoolMap
from app.services.reading import ReadingService
from app.clients.spoolman import get_spoolman_client, SpoolmanClient
from app.config import get_settings

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/", response_model=TagListResponse)
def list_tags(db: Session = Depends(get_db)):
    """List all tags with their current state."""
    tags = db.query(Tag).all()
    
    tag_responses = []
    for tag in tags:
        spool_state = db.query(SpoolState).filter(SpoolState.uid == tag.uid).first()
        spool_map = db.query(SpoolMap).filter(SpoolMap.uid == tag.uid).first()
        
        tag_data = {
            "uid": tag.uid,
            "created_at": tag.created_at,
            "last_seen_at": tag.last_seen_at,
            "notes": tag.notes,
            "spoolman_spool_id": spool_map.spoolman_spool_id if spool_map else None,
            "gross_weight_g": spool_state.gross_weight_g if spool_state else None,
            "tare_weight_g": spool_state.tare_weight_g if spool_state else None,
            "net_weight_g": spool_state.net_weight_g if spool_state else None,
            "status": spool_state.status if spool_state else None,
        }
        tag_responses.append(TagResponse(**tag_data))
    
    return TagListResponse(tags=tag_responses, total=len(tag_responses))


@router.get("/{uid}", response_model=TagResponse)
def get_tag(uid: str, db: Session = Depends(get_db)):
    """Get details of a specific tag."""
    tag = db.query(Tag).filter(Tag.uid == uid).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    spool_state = db.query(SpoolState).filter(SpoolState.uid == uid).first()
    spool_map = db.query(SpoolMap).filter(SpoolMap.uid == uid).first()
    
    tag_data = {
        "uid": tag.uid,
        "created_at": tag.created_at,
        "last_seen_at": tag.last_seen_at,
        "notes": tag.notes,
        "spoolman_spool_id": spool_map.spoolman_spool_id if spool_map else None,
        "gross_weight_g": spool_state.gross_weight_g if spool_state else None,
        "tare_weight_g": spool_state.tare_weight_g if spool_state else None,
        "net_weight_g": spool_state.net_weight_g if spool_state else None,
        "status": spool_state.status if spool_state else None,
    }
    
    return TagResponse(**tag_data)


@router.post("/{uid}/assign")
def assign_spool(
    uid: str,
    request: AssignSpoolRequest,
    db: Session = Depends(get_db),
    spoolman_client: SpoolmanClient = Depends(get_spoolman_client)
):
    """Assign a Spoolman spool ID to a tag."""
    service = ReadingService(db, spoolman_client)
    success = service.assign_spool(
        uid=uid,
        spoolman_spool_id=request.spoolman_spool_id,
        assigned_by=request.assigned_by
    )
    
    if success:
        return {"success": True, "message": f"Assigned spool {request.spoolman_spool_id} to tag {uid}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to assign spool")


@router.post("/{uid}/tare")
def tare_tag(
    uid: str,
    request: TareRequest,
    db: Session = Depends(get_db),
    spoolman_client: SpoolmanClient = Depends(get_spoolman_client)
):
    """Set tare weight for a tag."""
    service = ReadingService(db, spoolman_client)
    success = service.set_tare(uid=uid, tare_weight_g=request.tare_weight_g)
    
    if success:
        return {"success": True, "message": f"Set tare weight to {request.tare_weight_g}g for tag {uid}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to set tare weight")


@router.post("/{uid}/write_openspools", response_model=OpenSpoolWriteResponse)
def write_openspool_data(
    uid: str,
    request: OpenSpoolWriteRequest,
    db: Session = Depends(get_db)
):
    """
    Generate OpenSpool-compatible JSON payload for NFC writing.
    
    Note: This endpoint only generates the payload. Actual NFC writing
    must be done by external hardware/software.
    """
    settings = get_settings()
    
    if not settings.write_mode and not request.force:
        raise HTTPException(
            status_code=403,
            detail="Write mode is disabled. Set WRITE_MODE=true or use force=true parameter"
        )
    
    # Get tag info
    tag = db.query(Tag).filter(Tag.uid == uid).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    spool_map = db.query(SpoolMap).filter(SpoolMap.uid == uid).first()
    if not spool_map:
        raise HTTPException(status_code=404, detail="Tag not assigned to any spool")
    
    # Generate OpenSpool payload
    # This is a simplified example - actual OpenSpool format may differ
    payload = {
        "version": 1,
        "uid": uid,
        "spool_id": spool_map.spoolman_spool_id,
        "type": "openspool"
    }
    
    return OpenSpoolWriteResponse(
        success=True,
        message="OpenSpool payload generated. Use external NFC writer to write this data.",
        payload=payload
    )
