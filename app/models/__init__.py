"""Database models."""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class Device(Base):
    """Scale device model."""
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    device_id = Column(String, unique=True, nullable=False, index=True)
    location = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Tag(Base):
    """NFC tag model."""
    __tablename__ = "tags"
    
    uid = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), onupdate=func.now())
    notes = Column(Text, nullable=True)


class SpoolMap(Base):
    """Mapping between NFC UID and Spoolman spool ID."""
    __tablename__ = "spools_map"
    
    uid = Column(String, ForeignKey("tags.uid"), primary_key=True, index=True)
    spoolman_spool_id = Column(Integer, nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(String, nullable=True)


class SpoolState(Base):
    """Current state of a spool."""
    __tablename__ = "spool_state"
    
    uid = Column(String, ForeignKey("tags.uid"), primary_key=True, index=True)
    gross_weight_g = Column(Float, nullable=True)
    tare_weight_g = Column(Float, nullable=True)
    net_weight_g = Column(Float, nullable=True)
    last_weight_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=True)


class SpoolMetaCache(Base):
    """Cached metadata from Spoolman."""
    __tablename__ = "spool_meta_cache"
    
    spoolman_spool_id = Column(Integer, primary_key=True, index=True)
    brand = Column(String, nullable=True)
    material = Column(String, nullable=True)
    color = Column(String, nullable=True)
    diameter = Column(Float, nullable=True)
    temp_min = Column(Integer, nullable=True)
    temp_max = Column(Integer, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PrinterBinding(Base):
    """Binding between NFC tag and printer slot."""
    __tablename__ = "printer_binding"
    
    uid = Column(String, ForeignKey("tags.uid"), primary_key=True, index=True)
    printer_type = Column(String, nullable=False)  # bambulab or klipper
    printer_name = Column(String, nullable=False)
    slot_id = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WeightReading(Base):
    """Historical weight readings."""
    __tablename__ = "weight_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=False, index=True)
    uid = Column(String, ForeignKey("tags.uid"), nullable=False, index=True)
    gross_weight_g = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
