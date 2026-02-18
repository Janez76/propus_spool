"""Service for Spoolman synchronization."""
from sqlalchemy.orm import Session
from app.models import SpoolMap, SpoolMetaCache, SpoolState
from app.clients.spoolman import SpoolmanClient


class SpoolmanSyncService:
    """Service for synchronizing data with Spoolman."""
    
    def __init__(self, db: Session, spoolman_client: SpoolmanClient):
        self.db = db
        self.spoolman = spoolman_client
    
    async def pull_metadata(self) -> dict:
        """Pull spool metadata from Spoolman and cache it locally."""
        spools = await self.spoolman.list_spools()
        synced_count = 0
        
        for spool_data in spools:
            spool_id = spool_data.get("id")
            if not spool_id:
                continue
            
            # Extract filament info
            filament = spool_data.get("filament", {})
            
            # Update or create cache entry
            cache_entry = self.db.query(SpoolMetaCache).filter(
                SpoolMetaCache.spoolman_spool_id == spool_id
            ).first()
            
            if not cache_entry:
                cache_entry = SpoolMetaCache(spoolman_spool_id=spool_id)
                self.db.add(cache_entry)
            
            # Update fields
            cache_entry.brand = filament.get("vendor", {}).get("name")
            cache_entry.material = filament.get("material")
            cache_entry.color = filament.get("color_hex")
            cache_entry.diameter = filament.get("diameter")
            cache_entry.temp_min = filament.get("settings_extruder_temp")
            cache_entry.temp_max = filament.get("settings_bed_temp")
            
            synced_count += 1
        
        self.db.commit()
        
        return {
            "success": True,
            "synced_count": synced_count,
            "message": f"Successfully synced {synced_count} spools from Spoolman"
        }
    
    async def push_weight(self, uid: str) -> bool:
        """Push current weight of a tag to Spoolman."""
        # Get spool mapping
        spool_map = self.db.query(SpoolMap).filter(SpoolMap.uid == uid).first()
        if not spool_map:
            return False
        
        # Get current state
        spool_state = self.db.query(SpoolState).filter(SpoolState.uid == uid).first()
        if not spool_state or spool_state.net_weight_g is None:
            return False
        
        # Push to Spoolman
        success = await self.spoolman.update_spool_weight(
            spool_map.spoolman_spool_id,
            spool_state.net_weight_g
        )
        
        return success
