"""
Service for Spoolman synchronization
"""
from sqlalchemy.orm import Session
from app.models import SpoolMap, SpoolState, SpoolMetaCache
from app.schemas import SyncResponse
from app.clients.spoolman import SpoolmanClient
from app.config import settings
import logging

logger = logging.getLogger(__name__)


async def pull_from_spoolman(db: Session) -> SyncResponse:
    """
    Pull spool metadata from Spoolman and update local cache
    
    Fetches metadata for all mapped spools
    """
    if not settings.spoolman_url:
        return SyncResponse(
            success=False,
            message="Spoolman URL not configured"
        )
    
    client = SpoolmanClient(settings.spoolman_url, settings.spoolman_api_key)
    
    # Get all spool mappings
    mappings = db.query(SpoolMap).all()
    
    synced_count = 0
    for mapping in mappings:
        try:
            # Fetch spool metadata from Spoolman
            spool_data = await client.get_spool(mapping.spoolman_spool_id)
            
            if spool_data:
                # Update or create cache entry
                cache = db.query(SpoolMetaCache).filter(
                    SpoolMetaCache.spoolman_spool_id == mapping.spoolman_spool_id
                ).first()
                
                if not cache:
                    cache = SpoolMetaCache(spoolman_spool_id=mapping.spoolman_spool_id)
                    db.add(cache)
                
                # Update metadata
                filament = spool_data.get("filament", {})
                cache.brand = filament.get("vendor", {}).get("name")
                cache.material = filament.get("material")
                cache.color = filament.get("color_hex")
                cache.diameter = filament.get("diameter")
                cache.temp_min = filament.get("settings_extruder_temp")
                cache.temp_max = filament.get("settings_bed_temp")
                
                synced_count += 1
        except Exception as e:
            logger.warning(f"Failed to sync spool {mapping.spoolman_spool_id}: {e}")
    
    db.commit()
    
    return SyncResponse(
        success=True,
        message=f"Synced {synced_count} spools from Spoolman",
        synced_count=synced_count
    )


async def push_to_spoolman(db: Session, uid: str) -> SyncResponse:
    """
    Push weight update to Spoolman
    
    Updates the remaining weight for a spool in Spoolman
    """
    if not settings.spoolman_url:
        return SyncResponse(
            success=False,
            message="Spoolman URL not configured"
        )
    
    # Get spool mapping
    mapping = db.query(SpoolMap).filter(SpoolMap.uid == uid).first()
    if not mapping:
        raise ValueError(f"No Spoolman mapping found for tag {uid}")
    
    # Get spool state
    state = db.query(SpoolState).filter(SpoolState.uid == uid).first()
    if not state or state.net_weight_g is None:
        raise ValueError(f"No weight data found for tag {uid}")
    
    # Push to Spoolman
    client = SpoolmanClient(settings.spoolman_url, settings.spoolman_api_key)
    
    try:
        # Convert grams to Spoolman's expected unit (usually grams)
        await client.update_spool_weight(
            mapping.spoolman_spool_id,
            state.net_weight_g
        )
        
        logger.info(f"Pushed {state.net_weight_g}g to Spoolman for spool {mapping.spoolman_spool_id}")
        
        return SyncResponse(
            success=True,
            message=f"Updated Spoolman spool {mapping.spoolman_spool_id} with {state.net_weight_g}g"
        )
    except Exception as e:
        logger.error(f"Failed to push to Spoolman: {e}")
        raise
