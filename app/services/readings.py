"""
Service for processing weight readings
"""
from sqlalchemy.orm import Session
from datetime import datetime
from app.models import Tag, WeightReading, SpoolState, Device
from app.schemas import WeightReadingCreate
from app.config import settings
from app.services.sync import push_to_spoolman
import logging

logger = logging.getLogger(__name__)


async def process_reading(db: Session, reading: WeightReadingCreate) -> dict:
    """
    Process a weight reading from a scale device
    
    Steps:
    1. Ensure device exists
    2. Upsert tag
    3. Store reading in history
    4. Update spool state
    5. Calculate net weight
    6. Push to Spoolman if enabled
    """
    # Use provided timestamp or current time
    timestamp = reading.timestamp or datetime.utcnow()
    
    # 1. Ensure device exists (create if not)
    device = db.query(Device).filter(Device.device_id == reading.device_id).first()
    if not device:
        device = Device(
            device_id=reading.device_id,
            name=reading.device_id
        )
        db.add(device)
        db.commit()
        logger.info(f"Created new device: {reading.device_id}")
    
    # 2. Upsert tag
    tag = db.query(Tag).filter(Tag.uid == reading.uid).first()
    if not tag:
        tag = Tag(uid=reading.uid)
        db.add(tag)
        logger.info(f"Created new tag: {reading.uid}")
    else:
        tag.last_seen_at = timestamp
    db.commit()
    
    # 3. Store reading in history
    weight_reading = WeightReading(
        device_id=reading.device_id,
        uid=reading.uid,
        gross_weight_g=reading.gross_weight_g,
        created_at=timestamp
    )
    db.add(weight_reading)
    db.commit()
    
    # 4. Update or create spool state
    spool_state = db.query(SpoolState).filter(SpoolState.uid == reading.uid).first()
    if not spool_state:
        spool_state = SpoolState(
            uid=reading.uid,
            gross_weight_g=reading.gross_weight_g,
            tare_weight_g=0.0,
            net_weight_g=reading.gross_weight_g,
            last_weight_at=timestamp,
            status="active"
        )
        db.add(spool_state)
    else:
        spool_state.gross_weight_g = reading.gross_weight_g
        spool_state.net_weight_g = reading.gross_weight_g - (spool_state.tare_weight_g or 0.0)
        spool_state.last_weight_at = timestamp
    
    db.commit()
    db.refresh(spool_state)
    
    # 5. Push to Spoolman if enabled
    spoolman_pushed = False
    if settings.push_remaining_to_spoolman and settings.spoolman_url:
        try:
            await push_to_spoolman(db, reading.uid)
            spoolman_pushed = True
            logger.info(f"Pushed weight update to Spoolman for {reading.uid}")
        except Exception as e:
            logger.warning(f"Failed to push to Spoolman: {e}")
    
    return {
        "success": True,
        "uid": reading.uid,
        "gross_weight_g": spool_state.gross_weight_g,
        "tare_weight_g": spool_state.tare_weight_g,
        "net_weight_g": spool_state.net_weight_g,
        "spoolman_pushed": spoolman_pushed,
        "timestamp": timestamp.isoformat()
    }
