"""Service for handling weight readings and tag operations."""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Tag, SpoolState, WeightReading, Device, SpoolMap
from app.clients.spoolman import SpoolmanClient
from app.config import get_settings


class ReadingService:
    """Service for processing weight readings."""
    
    def __init__(self, db: Session, spoolman_client: SpoolmanClient):
        self.db = db
        self.spoolman = spoolman_client
        self.settings = get_settings()
    
    async def process_reading(
        self,
        device_id: str,
        uid: str,
        gross_weight_g: float,
        timestamp: Optional[datetime] = None
    ) -> dict:
        """
        Process a weight reading from a scale device.
        
        Logic:
        1. Ensure device exists
        2. Upsert tag
        3. Store reading in history
        4. Calculate net weight
        5. Update spool state
        6. Optionally push to Spoolman
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Ensure device exists
        device = self.db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            # Auto-create device if it doesn't exist
            device = Device(device_id=device_id, name=device_id)
            self.db.add(device)
            self.db.commit()
        
        # Upsert tag
        tag = self.db.query(Tag).filter(Tag.uid == uid).first()
        if not tag:
            tag = Tag(uid=uid, created_at=timestamp)
            self.db.add(tag)
        tag.last_seen_at = timestamp
        
        # Store reading in history
        reading = WeightReading(
            device_id=device_id,
            uid=uid,
            gross_weight_g=gross_weight_g,
            created_at=timestamp
        )
        self.db.add(reading)
        
        # Get or create spool state
        spool_state = self.db.query(SpoolState).filter(SpoolState.uid == uid).first()
        if not spool_state:
            spool_state = SpoolState(
                uid=uid,
                gross_weight_g=gross_weight_g,
                tare_weight_g=0.0,
                net_weight_g=gross_weight_g,
                last_weight_at=timestamp,
                status="active"
            )
            self.db.add(spool_state)
        else:
            spool_state.gross_weight_g = gross_weight_g
            # Calculate net weight
            tare = spool_state.tare_weight_g or 0.0
            spool_state.net_weight_g = gross_weight_g - tare
            spool_state.last_weight_at = timestamp
        
        self.db.commit()
        self.db.refresh(spool_state)
        
        # Push to Spoolman if enabled
        if self.settings.push_remaining_to_spoolman:
            spool_map = self.db.query(SpoolMap).filter(SpoolMap.uid == uid).first()
            if spool_map:
                await self.spoolman.update_spool_weight(
                    spool_map.spoolman_spool_id,
                    spool_state.net_weight_g or 0.0
                )
        
        return {
            "success": True,
            "uid": uid,
            "gross_weight_g": spool_state.gross_weight_g,
            "net_weight_g": spool_state.net_weight_g,
            "tare_weight_g": spool_state.tare_weight_g
        }
    
    def set_tare(self, uid: str, tare_weight_g: float) -> bool:
        """Set tare weight for a tag."""
        spool_state = self.db.query(SpoolState).filter(SpoolState.uid == uid).first()
        if not spool_state:
            # Create new spool state with tare
            spool_state = SpoolState(
                uid=uid,
                tare_weight_g=tare_weight_g,
                status="active"
            )
            self.db.add(spool_state)
        else:
            spool_state.tare_weight_g = tare_weight_g
            # Recalculate net weight if we have gross weight
            if spool_state.gross_weight_g is not None:
                spool_state.net_weight_g = spool_state.gross_weight_g - tare_weight_g
        
        self.db.commit()
        return True
    
    def assign_spool(self, uid: str, spoolman_spool_id: int, assigned_by: Optional[str] = None) -> bool:
        """Assign a Spoolman spool ID to a tag."""
        # Ensure tag exists
        tag = self.db.query(Tag).filter(Tag.uid == uid).first()
        if not tag:
            tag = Tag(uid=uid)
            self.db.add(tag)
            self.db.commit()
        
        # Create or update spool map
        spool_map = self.db.query(SpoolMap).filter(SpoolMap.uid == uid).first()
        if not spool_map:
            spool_map = SpoolMap(
                uid=uid,
                spoolman_spool_id=spoolman_spool_id,
                assigned_by=assigned_by
            )
            self.db.add(spool_map)
        else:
            spool_map.spoolman_spool_id = spoolman_spool_id
            spool_map.assigned_by = assigned_by
            spool_map.assigned_at = datetime.utcnow()
        
        self.db.commit()
        return True
