"""
HTTP client for Spoolman API integration
"""
import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SpoolmanClient:
    """Client for interacting with Spoolman API"""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    async def get_spool(self, spool_id: int) -> Optional[Dict[str, Any]]:
        """
        Get spool data from Spoolman
        
        Args:
            spool_id: Spoolman spool ID
            
        Returns:
            Spool data dict or None if not found
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/spool/{spool_id}",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.warning(f"Spool {spool_id} not found in Spoolman")
                    return None
                else:
                    logger.error(f"Spoolman API error: {response.status_code}")
                    response.raise_for_status()
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Spoolman: {e}")
            raise
    
    async def update_spool_weight(self, spool_id: int, weight_g: float) -> bool:
        """
        Update remaining weight in Spoolman
        
        Args:
            spool_id: Spoolman spool ID
            weight_g: Remaining weight in grams
            
        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.base_url}/api/v1/spool/{spool_id}",
                    headers=self.headers,
                    json={"remaining_weight": weight_g},
                    timeout=10.0
                )
                
                if response.status_code in (200, 204):
                    logger.info(f"Updated spool {spool_id} weight to {weight_g}g")
                    return True
                else:
                    logger.error(f"Failed to update spool weight: {response.status_code}")
                    response.raise_for_status()
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Spoolman: {e}")
            raise
    
    async def list_spools(self, limit: int = 100, offset: int = 0) -> list[Dict[str, Any]]:
        """
        List spools from Spoolman
        
        Args:
            limit: Maximum number of spools to return
            offset: Offset for pagination
            
        Returns:
            List of spool data dicts
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/spool",
                    headers=self.headers,
                    params={"limit": limit, "offset": offset},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to list spools: {response.status_code}")
                    response.raise_for_status()
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Spoolman: {e}")
            raise
