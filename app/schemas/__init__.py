"""Pydantic schemas for API request/response validation."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# Reading schemas
class ReadingCreate(BaseModel):
    """Schema for creating a weight reading."""
    device_id: str
    uid: str
    gross_weight_g: float
    timestamp: Optional[datetime] = None


class ReadingResponse(BaseModel):
    """Schema for reading response."""
    success: bool
    uid: str
    gross_weight_g: float
    net_weight_g: Optional[float] = None
    tare_weight_g: Optional[float] = None
    message: Optional[str] = None


# Tag schemas
class TagBase(BaseModel):
    """Base tag schema."""
    uid: str
    notes: Optional[str] = None


class TagResponse(BaseModel):
    """Schema for tag response."""
    uid: str
    created_at: datetime
    last_seen_at: Optional[datetime] = None
    notes: Optional[str] = None
    spoolman_spool_id: Optional[int] = None
    gross_weight_g: Optional[float] = None
    tare_weight_g: Optional[float] = None
    net_weight_g: Optional[float] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


class TagListResponse(BaseModel):
    """Schema for tag list response."""
    tags: list[TagResponse]
    total: int


# Assignment schemas
class AssignSpoolRequest(BaseModel):
    """Schema for assigning a spool to a tag."""
    spoolman_spool_id: int
    assigned_by: Optional[str] = None


class TareRequest(BaseModel):
    """Schema for taring a scale."""
    tare_weight_g: float


# Spoolman sync schemas
class SpoolmanSyncResponse(BaseModel):
    """Schema for Spoolman sync response."""
    success: bool
    synced_count: int
    message: Optional[str] = None


# OpenSpool schemas
class OpenSpoolWriteRequest(BaseModel):
    """Schema for writing OpenSpool data to NFC tag."""
    force: bool = False


class OpenSpoolWriteResponse(BaseModel):
    """Schema for OpenSpool write response."""
    success: bool
    message: str
    payload: Optional[dict] = None
