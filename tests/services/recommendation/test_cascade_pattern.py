"""
Unit tests for PAT-02: Template Method for Resolution Cascade.
"""

import pytest
from unittest.mock import MagicMock
from src.services.recommendation.resolution_cascade import (
    BaseResolutionCascade, 
    ResolutionAttempt, 
    ResolutionStrategy,
    StandardResolutionCascade
)
from src.schemas.hardware import HardwareProfile
from src.schemas.model import ModelEntry

class MockCascade(BaseResolutionCascade):
    """Subclass to test the template method hooks."""
    def try_quantization(self, m, h): return ResolutionAttempt(ResolutionStrategy.QUANTIZATION, False)
    def try_cpu_offload(self, m, h): return ResolutionAttempt(ResolutionStrategy.CPU_OFFLOAD, False)
    def try_substitution(self, m, h, u): return ResolutionAttempt(ResolutionStrategy.SUBSTITUTION, True, details="Mock Sub")
    def try_workflow_adjustment(self, m, h, u): return ResolutionAttempt(ResolutionStrategy.WORKFLOW_ADJUSTMENT, False)
    def try_cloud_fallback(self, m, u): return ResolutionAttempt(ResolutionStrategy.CLOUD_FALLBACK, False)

def test_template_method_flow():
    """Verify that resolve() calls steps in order and stops at first success."""
    cascade = MockCascade(model_database={})
    model = MagicMock(spec=ModelEntry)
    model.id = "test"
    hardware = MagicMock(spec=HardwareProfile)
    
    result = cascade.resolve(model, hardware, "fail", "image")
    
    assert result.resolved is True
    assert result.final_strategy == ResolutionStrategy.SUBSTITUTION
    assert len(result.attempts) == 3 # Quant, Offload, Sub
    assert result.user_message == "Mock Sub"

def test_standard_cascade_cloud_fallback(monkeypatch):
    """Verify standard cascade falls back to cloud if all local steps fail."""
    cascade = StandardResolutionCascade(model_database={})
    model = MagicMock(spec=ModelEntry)
    model.id = "heavy_model"
    model.name = "Heavy Model"
    model.family = "flux"
    model.variants = [] # No variants -> all local steps will fail
    
    hardware = MagicMock(spec=HardwareProfile)
    hardware.vram_gb = 4.0
    hardware.platform = "win32"
    hardware.ram = None
    
    # Force workflow adjustment to fail for this test
    monkeypatch.setattr(cascade, "try_workflow_adjustment", lambda m, h, u: ResolutionAttempt(ResolutionStrategy.WORKFLOW_ADJUSTMENT, False))
    
    result = cascade.resolve(model, hardware, "vram", "image")
    
    assert result.resolved is True
    assert result.final_strategy == ResolutionStrategy.CLOUD_FALLBACK
    assert "Cloud API" in result.user_message
