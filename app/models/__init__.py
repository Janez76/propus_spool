"""
Database models for propus_spool
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base


class Device(Base):
    """ESP32 scale devices"""
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    device_id = Column(String, unique=True, nullable=False, index=True)
    location = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Tag(Base):
    """NFC tags (NTAG215) tracked by UID"""
    __tablename__ = "tags"
    
    uid = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), onupdate=func.now())
    notes = Column(Text)


class SpoolMap(Base):
    """Mapping between NFC UIDs and Spoolman spool IDs"""
    __tablename__ = "spools_map"
    
    uid = Column(String, ForeignKey("tags.uid"), primary_key=True)
    spoolman_spool_id = Column(Integer, nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_by = Column(String)


class SpoolState(Base):
    """Current state of each spool (weight, status)"""
    __tablename__ = "spool_state"
    
    uid = Column(String, ForeignKey("tags.uid"), primary_key=True)
    gross_weight_g = Column(Float)
    tare_weight_g = Column(Float, default=0.0)
    net_weight_g = Column(Float)
    last_weight_at = Column(DateTime(timezone=True))
    status = Column(String, default="active")  # active, empty, archived


class SpoolMetaCache(Base):
    """Cached metadata from Spoolman"""
    __tablename__ = "spool_meta_cache"
    
    spoolman_spool_id = Column(Integer, primary_key=True, index=True)
    brand = Column(String)
    material = Column(String)
    color = Column(String)
    diameter = Column(Float)
    temp_min = Column(Integer)
    temp_max = Column(Integer)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PrinterBinding(Base):
    """Binding between spools and printer slots"""
    __tablename__ = "printer_binding"
    
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String, ForeignKey("tags.uid"), nullable=False)
    printer_type = Column(String, nullable=False)  # bambulab, klipper
    printer_name = Column(String, nullable=False)
    slot_id = Column(String)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WeightReading(Base):
    """Historical weight readings from scales"""
    __tablename__ = "weight_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=False, index=True)
    uid = Column(String, ForeignKey("tags.uid"), nullable=False, index=True)
    gross_weight_g = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
