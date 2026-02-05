"""
Unit tests for DB-02: Hardware Profile Snapshotting.
"""

import pytest
import os
from pathlib import Path
from src.services.hardware_snapshot_service import HardwareSnapshotService
from src.services.database.engine import DatabaseManager
from src.schemas.hardware import HardwareProfile, PlatformType, CPUTier
from src.services.database.models import HardwareSnapshot

# Use a temporary test database
SNAPSHOT_TEST_DB = Path("data/test_snapshots.db")

@pytest.fixture
def snapshot_service(monkeypatch):
    """Provides a HardwareSnapshotService with a clean test database."""
    if SNAPSHOT_TEST_DB.exists():
        try: os.remove(SNAPSHOT_TEST_DB)
        except: pass
    
    manager = DatabaseManager(db_path=SNAPSHOT_TEST_DB)
    manager.init_db()
    
    from src.services import hardware_snapshot_service
    monkeypatch.setattr(hardware_snapshot_service, "db_manager", manager)
    
    service = HardwareSnapshotService()
    yield service
    
    manager.engine.dispose()
    if SNAPSHOT_TEST_DB.exists():
        try: os.remove(SNAPSHOT_TEST_DB)
        except: pass

def test_take_snapshot(snapshot_service):
    """Verify that a HardwareProfile is correctly persisted as a snapshot."""
    from unittest.mock import MagicMock
    from src.schemas.hardware import CPUProfile, RAMProfile, StorageProfile
    
    profile = HardwareProfile(
        platform=PlatformType.WINDOWS_NVIDIA,
        gpu_vendor="nvidia",
        gpu_name="RTX 4090",
        vram_gb=24.0,
        compute_capability=8.9,
        cpu=CPUProfile(model="Intel i9", architecture="x86_64", physical_cores=16, logical_cores=32, tier=CPUTier.HIGH),
        ram=RAMProfile(total_gb=64.0, available_gb=48.0, usable_for_offload_gb=32.0),
        storage=StorageProfile(path="C:", total_gb=1000.0, free_gb=500.0, storage_type="nvme", estimated_read_mbps=7000)
    )
    
    snapshot = snapshot_service.take_snapshot(profile)
    assert snapshot.gpu_name == "RTX 4090"
    assert snapshot.vram_gb == 24.0
    assert snapshot.cpu_tier == "high"
    assert snapshot.ram_gb == 64.0
    assert snapshot.storage_free_gb == 500.0
    assert snapshot.compute_capability == 8.9

def test_get_latest_snapshot(snapshot_service):
    """Verify retrieval of the most recent snapshot."""
    from src.schemas.hardware import HardwareProfile, PlatformType
    
    p1 = HardwareProfile(platform=PlatformType.CPU_ONLY, gpu_vendor="none", gpu_name="Old", vram_gb=0.0)
    p2 = HardwareProfile(platform=PlatformType.WINDOWS_NVIDIA, gpu_vendor="nvidia", gpu_name="New", vram_gb=8.0)
    
    snapshot_service.take_snapshot(p1)
    import time
    time.sleep(0.1)
    snapshot_service.take_snapshot(p2)
    
    latest = snapshot_service.get_latest_snapshot()
    assert latest.gpu_name == "New"

def test_get_history(snapshot_service):
    """Verify history limit and ordering."""
    from src.schemas.hardware import HardwareProfile, PlatformType
    
    for i in range(5):
        p = HardwareProfile(platform=PlatformType.CPU_ONLY, gpu_vendor="none", gpu_name=f"GPU_{i}", vram_gb=0.0)
        snapshot_service.take_snapshot(p)
        
    history = snapshot_service.get_history(limit=3)
    assert len(history) == 3
    assert history[0].gpu_name == "GPU_4"
    assert history[1].gpu_name == "GPU_3"
    assert history[2].gpu_name == "GPU_2"
