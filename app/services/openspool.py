"""
Service for OpenSpool tag writing (optional feature)
"""
from sqlalchemy.orm import Session
from app.models import SpoolMap, SpoolMetaCache, SpoolState
from app.schemas import OpenSpoolWriteResponse
import logging

logger = logging.getLogger(__name__)


async def write_openspool_tag(db: Session, uid: str) -> OpenSpoolWriteResponse:
    """
    Generate OpenSpool-compatible JSON payload and prepare for NFC write
    
    This is a stub implementation - actual NFC writing would require hardware integration
    """
    # Get spool mapping
    mapping = db.query(SpoolMap).filter(SpoolMap.uid == uid).first()
    if not mapping:
        raise ValueError(f"No Spoolman mapping found for tag {uid}")
    
    # Get metadata
    meta = db.query(SpoolMetaCache).filter(
        SpoolMetaCache.spoolman_spool_id == mapping.spoolman_spool_id
    ).first()
    
    # Get state
    state = db.query(SpoolState).filter(SpoolState.uid == uid).first()
    
    # Build OpenSpool payload
    payload = {
        "version": 1,
        "uid": uid,
        "manufacturer": meta.brand if meta else "Unknown",
        "material": meta.material if meta else "Unknown",
        "color": meta.color if meta else "Unknown",
        "diameter": meta.diameter if meta else 1.75,
        "weight": state.net_weight_g if state else 0.0,
        "temperature": {
            "min": meta.temp_min if meta else 200,
            "max": meta.temp_max if meta else 240
        }
    }
    
    logger.info(f"Generated OpenSpool payload for {uid}")
    logger.warning("Actual NFC write not implemented - would require hardware integration")
    
    return OpenSpoolWriteResponse(
        success=True,
        message="OpenSpool payload generated (NFC write stub - hardware integration needed)",
        payload=payload
    )
