"""
Pydantic schemas for API requests and responses
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# Weight Reading Schemas
class WeightReadingCreate(BaseModel):
    """Schema for creating a weight reading"""
    device_id: str = Field(..., description="Device identifier (e.g., 'scale01')")
    uid: str = Field(..., description="NFC tag UID (e.g., '04AABBCCDD')")
    gross_weight_g: float = Field(..., description="Gross weight in grams")
    timestamp: Optional[datetime] = Field(None, description="ISO8601 timestamp")


class WeightReadingResponse(BaseModel):
    """Schema for weight reading response"""
    id: int
    device_id: str
    uid: str
    gross_weight_g: float
    created_at: datetime
    
    class Config:
        from_attributes = True


# Tag Schemas
class TagBase(BaseModel):
    """Base tag schema"""
    uid: str
    notes: Optional[str] = None


class TagCreate(TagBase):
    """Schema for creating a tag"""
    pass


class TagResponse(TagBase):
    """Schema for tag response"""
    created_at: datetime
    last_seen_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TagDetailResponse(TagResponse):
    """Detailed tag response with related data"""
    spool_mapping: Optional[dict] = None  # Will be SpoolMapResponse
    spool_state: Optional[dict] = None  # Will be SpoolStateResponse


# Spool Map Schemas
class SpoolMapCreate(BaseModel):
    """Schema for assigning a spool to a tag"""
    spoolman_spool_id: int
    assigned_by: Optional[str] = None


class SpoolMapResponse(BaseModel):
    """Schema for spool map response"""
    uid: str
    spoolman_spool_id: int
    assigned_at: datetime
    assigned_by: Optional[str] = None
    
    class Config:
        from_attributes = True


# Spool State Schemas
class SpoolStateResponse(BaseModel):
    """Schema for spool state response"""
    uid: str
    gross_weight_g: Optional[float] = None
    tare_weight_g: Optional[float] = None
    net_weight_g: Optional[float] = None
    last_weight_at: Optional[datetime] = None
    status: str = "active"
    
    class Config:
        from_attributes = True


class TareRequest(BaseModel):
    """Schema for setting tare weight"""
    tare_weight_g: float = Field(..., description="Tare weight in grams")


# Spool Meta Cache Schemas
class SpoolMetaCacheResponse(BaseModel):
    """Schema for spool metadata cache"""
    spoolman_spool_id: int
    brand: Optional[str] = None
    material: Optional[str] = None
    color: Optional[str] = None
    diameter: Optional[float] = None
    temp_min: Optional[int] = None
    temp_max: Optional[int] = None
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Device Schemas
class DeviceCreate(BaseModel):
    """Schema for creating a device"""
    name: str
    device_id: str
    location: Optional[str] = None


class DeviceResponse(BaseModel):
    """Schema for device response"""
    id: int
    name: str
    device_id: str
    location: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Sync Schemas
class SyncResponse(BaseModel):
    """Schema for sync operation response"""
    success: bool
    message: str
    synced_count: Optional[int] = None


# OpenSpool Schemas
class OpenSpoolWriteRequest(BaseModel):
    """Schema for OpenSpool write request"""
    force: bool = Field(False, description="Force write even if WRITE_MODE is false")


class OpenSpoolWriteResponse(BaseModel):
    """Schema for OpenSpool write response"""
    success: bool
    message: str
    payload: Optional[dict] = None


# Health Check Schema
class HealthResponse(BaseModel):
    """Schema for health check response"""
    status: str
    database: str
    spoolman: Optional[str] = None
