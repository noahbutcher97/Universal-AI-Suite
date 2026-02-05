"""
SQLAlchemy ORM models for the AI Universal Suite database.
Part of Task DB-01: YAML to SQLite Migration.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Model(Base):
    """
    High-level model definitions (corresponds to ModelEntry).
    """
    __tablename__ = "models"

    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    family = Column(String(100))
    release_date = Column(String(20))
    license = Column(String(100))
    commercial_use = Column(Boolean, default=False)
    category = Column(String(50), nullable=False, index=True)
    description = Column(Text)
    repository_url = Column(Text)
    is_cloud_api = Column(Boolean, default=False, index=True)
    provider = Column(String(100))
    
    # Nested data as JSON (for simplicity in v1, can be normalized later if needed)
    architecture = Column(JSON)
    capabilities = Column(JSON)
    dependencies = Column(JSON)
    explanation = Column(JSON)
    cloud = Column(JSON)
    hardware = Column(JSON)
    pricing = Column(JSON)

    # Relationships
    variants = relationship("ModelVariant", back_populates="model", cascade="all, delete-orphan")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Model(id='{self.id}', name='{self.name}', category='{self.category}')>"


class ModelVariant(Base):
    """
    Specific quantizations and hardware-specific builds (corresponds to ModelVariant).
    """
    __tablename__ = "model_variants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(100), ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True)
    variant_id = Column(String(100), nullable=False) # The 'id' from YAML (e.g. 'fp16', 'gguf_q4')
    precision = Column(String(50), nullable=False)
    vram_min_mb = Column(Integer, nullable=False, index=True)
    vram_recommended_mb = Column(Integer)
    download_size_gb = Column(Float)
    quality_retention_percent = Column(Integer, default=100)
    download_url = Column(Text)
    sha256 = Column(String(64))
    
    # Platform support as JSON
    platform_support = Column(JSON)
    requires_nodes = Column(JSON)
    notes = Column(Text)

    # Relationship to parent
    model = relationship("Model", back_populates="variants")

    def __repr__(self):
        return f"<ModelVariant(model='{self.model_id}', variant='{self.variant_id}', vram='{self.vram_min_mb}MB')>"


class HardwareSnapshot(Base):
    """
    Stores historical snapshots of hardware state at the time of a recommendation.
    Part of Task DB-02.
    """
    __tablename__ = "hardware_snapshots"

    id = Column(String(36), primary_key=True) # UUID
    gpu_vendor = Column(String(50))
    gpu_name = Column(String(255))
    vram_gb = Column(Float)
    compute_capability = Column(Float)
    cpu_tier = Column(String(20))
    ram_gb = Column(Float)
    storage_free_gb = Column(Float)
    raw_report = Column(JSON) # Full EnvironmentReport
    
    timestamp = Column(DateTime, default=datetime.utcnow)


class Installation(Base):
    """
    Tracks local file state and installation progress.
    Part of Task DB-03.
    """
    __tablename__ = "installations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_type = Column(String(50), default="model") # model, custom_node, tool
    model_id = Column(String(100), index=True)
    variant_db_id = Column(Integer, ForeignKey("model_variants.id"))
    
    status = Column(String(20), default="pending") # pending, downloading, installed, failed, corrupted
    local_path = Column(Text, unique=True) # Ensure path deduplication
    version = Column(String(50))
    
    current_bytes = Column(Integer, default=0)
    total_bytes = Column(Integer, default=0)
    checksum_verified = Column(Boolean, default=False)
    
    metadata_json = Column(JSON) # Store extra info like 'original_filename'
    
    installed_at = Column(DateTime, default=datetime.utcnow)
    last_verified_at = Column(DateTime)

    # Relationship for models
    variant = relationship("ModelVariant")


class DownloadTaskRecord(Base):
    """
    Persistent record of a download task for the queue.
    Part of Task SYS-02.
    """
    __tablename__ = "download_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, nullable=False)
    dest_path = Column(Text, nullable=False)
    expected_hash = Column(String(64))
    priority = Column(Integer, default=0)
    
    status = Column(String(20), default="pending") # pending, downloading, completed, failed, paused
    attempts = Column(Integer, default=0)
    last_error = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
