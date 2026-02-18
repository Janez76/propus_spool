"""
Service for tag management operations
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.models import Tag, SpoolMap, SpoolState
from app.schemas import TagResponse, TagDetailResponse, SpoolMapCreate, SpoolMapResponse, SpoolStateResponse
import logging

logger = logging.getLogger(__name__)


def list_tags(db: Session, skip: int = 0, limit: int = 100) -> List[TagResponse]:
    """List all tags"""
    tags = db.query(Tag).offset(skip).limit(limit).all()
    return [TagResponse.model_validate(tag) for tag in tags]


def get_tag_detail(db: Session, uid: str) -> Optional[TagDetailResponse]:
    """Get detailed tag information including mappings and state"""
    tag = db.query(Tag).filter(Tag.uid == uid).first()
    if not tag:
        return None
    
    # Get spool mapping
    spool_map = db.query(SpoolMap).filter(SpoolMap.uid == uid).first()
    spool_mapping = SpoolMapResponse.model_validate(spool_map) if spool_map else None
    
    # Get spool state
    spool_state = db.query(SpoolState).filter(SpoolState.uid == uid).first()
    state = SpoolStateResponse.model_validate(spool_state) if spool_state else None
    
    return TagDetailResponse(
        uid=tag.uid,
        created_at=tag.created_at,
        last_seen_at=tag.last_seen_at,
        notes=tag.notes,
        spool_mapping=spool_mapping,
        spool_state=state
    )


def assign_spool_to_tag(db: Session, uid: str, assignment: SpoolMapCreate) -> SpoolMapResponse:
    """Assign a Spoolman spool ID to a tag"""
    # Ensure tag exists
    tag = db.query(Tag).filter(Tag.uid == uid).first()
    if not tag:
        raise ValueError(f"Tag {uid} not found")
    
    # Create or update mapping
    spool_map = db.query(SpoolMap).filter(SpoolMap.uid == uid).first()
    if not spool_map:
        spool_map = SpoolMap(
            uid=uid,
            spoolman_spool_id=assignment.spoolman_spool_id,
            assigned_by=assignment.assigned_by
        )
        db.add(spool_map)
        logger.info(f"Created spool mapping: {uid} -> {assignment.spoolman_spool_id}")
    else:
        spool_map.spoolman_spool_id = assignment.spoolman_spool_id
        spool_map.assigned_at = datetime.utcnow()
        spool_map.assigned_by = assignment.assigned_by
        logger.info(f"Updated spool mapping: {uid} -> {assignment.spoolman_spool_id}")
    
    db.commit()
    db.refresh(spool_map)
    
    return SpoolMapResponse.model_validate(spool_map)


def set_tag_tare(db: Session, uid: str, tare_weight_g: float) -> dict:
    """Set tare weight for a tag and recalculate net weight"""
    # Ensure tag exists
    tag = db.query(Tag).filter(Tag.uid == uid).first()
    if not tag:
        raise ValueError(f"Tag {uid} not found")
    
    # Get or create spool state
    spool_state = db.query(SpoolState).filter(SpoolState.uid == uid).first()
    if not spool_state:
        spool_state = SpoolState(
            uid=uid,
            tare_weight_g=tare_weight_g,
            gross_weight_g=0.0,
            net_weight_g=-tare_weight_g,
            status="active"
        )
        db.add(spool_state)
    else:
        spool_state.tare_weight_g = tare_weight_g
        # Recalculate net weight
        spool_state.net_weight_g = (spool_state.gross_weight_g or 0.0) - tare_weight_g
    
    db.commit()
    db.refresh(spool_state)
    
    logger.info(f"Set tare for {uid}: {tare_weight_g}g")
    
    return {
        "success": True,
        "uid": uid,
        "tare_weight_g": spool_state.tare_weight_g,
        "gross_weight_g": spool_state.gross_weight_g,
        "net_weight_g": spool_state.net_weight_g
    }
