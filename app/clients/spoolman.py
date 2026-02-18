"""Spoolman API client."""
import httpx
from typing import Optional, Dict, Any
from app.config import get_settings


class SpoolmanClient:
    """Client for interacting with Spoolman API."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.spoolman_url.rstrip('/')
        self.api_key = self.settings.spoolman_api_key
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def get_spool(self, spool_id: int) -> Optional[Dict[str, Any]]:
        """Get spool details from Spoolman."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/spool/{spool_id}",
                    headers=self._get_headers(),
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Error fetching spool {spool_id} from Spoolman: {e}")
            return None
    
    async def update_spool_weight(self, spool_id: int, remaining_weight: float) -> bool:
        """Update remaining weight of a spool in Spoolman."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.base_url}/api/v1/spool/{spool_id}",
                    headers=self._get_headers(),
                    json={"remaining_weight": remaining_weight},
                    timeout=10.0
                )
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"Error updating spool {spool_id} in Spoolman: {e}")
            return False
    
    async def list_spools(self) -> list[Dict[str, Any]]:
        """List all spools from Spoolman."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/spool",
                    headers=self._get_headers(),
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Error listing spools from Spoolman: {e}")
            return []


def get_spoolman_client() -> SpoolmanClient:
    """Get Spoolman client instance."""
    return SpoolmanClient()
