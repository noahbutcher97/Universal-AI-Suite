"""
Hardware Snapshot Service.
Part of Task DB-02: Hardware Profile Snapshotting.

Stores historical snapshots of hardware state at the time of recommendations.
"""

import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.services.database.engine import db_manager
from src.services.database.models import HardwareSnapshot
from src.schemas.hardware import HardwareProfile
from src.utils.logger import log

class HardwareSnapshotService:
    """
    Handles capturing and retrieving hardware snapshots.
    """
    
    def __init__(self):
        db_manager.init_db()

    def take_snapshot(self, profile: HardwareProfile) -> HardwareSnapshot:
        """
        Captures the current HardwareProfile and saves it to the database.
        """
        session = db_manager.get_session()
        try:
            snapshot_id = str(uuid.uuid4())
            
            # Extract fields from modern HardwareProfile
            gpu_vendor = profile.gpu_vendor
            gpu_name = profile.gpu_name
            vram_gb = profile.vram_gb
            compute_capability = profile.compute_capability
            
            cpu_tier = profile.cpu.tier.value if profile.cpu else "unknown"
            ram_gb = profile.ram.total_gb if profile.ram else 0.0
            storage_free_gb = profile.storage.free_gb if profile.storage else 0.0
            
            # Serialize full profile for historical deep-dive
            # We convert to a dict first. Since HardwareProfile has nested dataclasses, 
            # we might need a helper or just use __dict__ if it's simple enough.
            # For now, let's just store a representative dict.
            raw_report = {
                "platform": profile.platform.value,
                "gpu_vendor": gpu_vendor,
                "gpu_name": gpu_name,
                "vram_gb": vram_gb,
                "unified_memory": profile.unified_memory,
                "compute_capability": compute_capability,
                "tier": profile.tier.value,
                "warnings": profile.warnings
            }

            new_snapshot = HardwareSnapshot(
                id=snapshot_id,
                gpu_vendor=gpu_vendor,
                gpu_name=gpu_name,
                vram_gb=vram_gb,
                compute_capability=compute_capability,
                cpu_tier=cpu_tier,
                ram_gb=ram_gb,
                storage_free_gb=storage_free_gb,
                raw_report=raw_report,
                timestamp=datetime.utcnow()
            )
            
            session.add(new_snapshot)
            session.commit()
            session.refresh(new_snapshot)
            session.expunge(new_snapshot)
            log.info(f"Captured hardware snapshot: {snapshot_id} ({gpu_name})")
            
            return new_snapshot
        finally:
            session.close()

    def get_latest_snapshot(self) -> Optional[HardwareSnapshot]:
        """
        Retrieve the most recent hardware snapshot.
        """
        session = db_manager.get_session()
        try:
            return session.query(HardwareSnapshot).order_by(HardwareSnapshot.timestamp.desc()).first()
        finally:
            session.close()

    def get_history(self, limit: int = 10) -> List[HardwareSnapshot]:
        """
        Retrieve snapshot history.
        """
        session = db_manager.get_session()
        try:
            return session.query(HardwareSnapshot).order_by(HardwareSnapshot.timestamp.desc()).limit(limit).all()
        finally:
            session.close()
