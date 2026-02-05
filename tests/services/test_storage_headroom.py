"""
Unit tests for SYS-05: Dynamic Storage Headroom Calculation.
"""

import pytest
from unittest.mock import patch
from src.services.system_service import SystemService
from src.services.recommendation.constraint_layer import ConstraintSatisfactionLayer
from src.schemas.recommendation import RejectionReason, PassingCandidate
from src.schemas.model import ModelEntry, ModelVariant

class TestStorageHeadroom:
    """Tests for storage headroom logic in SystemService and Constraint Layer."""

    @patch("src.services.system_service.SystemService.get_system_ram_gb")
    def test_headroom_calculation(self, mock_ram):
        """Verify the formula: (RAM * 0.5) + 10GB."""
        # 16GB RAM -> 8 + 10 = 18GB Headroom
        mock_ram.return_value = 16.0
        assert SystemService.get_required_headroom_gb() == 18.0
        
        # 64GB RAM -> 32 + 10 = 42GB Headroom
        mock_ram.return_value = 64.0
        assert SystemService.get_required_headroom_gb() == 42.0

    @patch("src.services.system_service.SystemService.get_disk_free_gb")
    @patch("src.services.system_service.SystemService.get_required_headroom_gb")
    def test_check_storage_headroom(self, mock_headroom, mock_free):
        """Verify the headroom check logic."""
        mock_headroom.return_value = 20.0
        
        # Case 1: Plenty of space
        # 100GB free, 20GB headroom, 10GB model -> 70GB buffer left -> Pass
        mock_free.return_value = 100.0
        assert SystemService.check_storage_headroom(10.0) is True
        
        # Case 2: Tight but fits
        # 35GB free, 20GB headroom, 15GB model -> 0GB buffer -> Pass
        mock_free.return_value = 35.0
        assert SystemService.check_storage_headroom(15.0) is True
        
        # Case 3: Violation
        # 30GB free, 20GB headroom, 15GB model -> -5GB buffer -> Fail
        mock_free.return_value = 30.0
        assert SystemService.check_storage_headroom(15.0) is False

    @patch("src.services.system_service.SystemService.check_storage_headroom")
    def test_constraint_layer_integration(self, mock_check, monkeypatch):
        """Regression test: verify ConstraintLayer correctly rejects models based on headroom."""
        from src.services.model_database import ModelDatabase
        from src.schemas.hardware import HardwareProfile, StorageProfile
        
        # Mock Model DB
        mock_db = patch("src.services.model_database.ModelDatabase").start()
        
        # Create dummy candidate
        variant = ModelVariant(
            id="v1", precision="fp16", vram_min_mb=4000, 
            vram_recommended_mb=6000, download_size_gb=10.0,
            platform_support={"windows_nvidia": {"supported": True}}
        )
        model = ModelEntry(
            id="m1", name="Model 1", family="test", category="image", 
            variants=[variant]
        )
        
        # Mock DB behavior
        mock_db.get_compatible_variants.return_value = [variant]
        
        layer = ConstraintSatisfactionLayer(model_db=mock_db)
        
        hardware = HardwareProfile(
            gpu_vendor="nvidia", gpu_name="RTX 3060", vram_gb=12.0, platform="windows_nvidia",
            storage=StorageProfile(path=".", total_gb=1000, free_gb=50.0, storage_type="ssd", estimated_read_mbps=500)
        )
        
        # Test 1: Headroom allows it
        mock_check.return_value = True
        result = layer._check_model(model, "windows_nvidia", 12000, 8.0, hardware)
        assert isinstance(result, PassingCandidate)
        
        # Test 2: Headroom rejects it
        mock_check.return_value = False
        result = layer._check_model(model, "windows_nvidia", 12000, 8.0, hardware)
        assert isinstance(result, RejectedCandidate)
        assert result.reason == RejectionReason.STORAGE_INSUFFICIENT
        assert "OS headroom" in result.details

# Helper to allow import of RejectedCandidate in tests
from src.services.recommendation.constraint_layer import RejectedCandidate
