"""
Unit and Integration tests for DB-03: Relational Installation Tracking.
"""

import pytest
import os
from pathlib import Path
from src.services.installation_service import InstallationService
from src.services.database.engine import DatabaseManager
from src.services.database.models import Model, ModelVariant, Installation

# Use a temporary test database
INST_TEST_DB = Path("data/test_installations.db")

@pytest.fixture
def inst_service(monkeypatch):
    """Provides an InstallationService with a clean test database."""
    if INST_TEST_DB.exists():
        try: os.remove(INST_TEST_DB)
        except: pass
    
    manager = DatabaseManager(db_path=INST_TEST_DB)
    manager.init_db()
    
    from src.services import installation_service
    monkeypatch.setattr(installation_service, "db_manager", manager)
    
    service = InstallationService()
    yield service
    
    manager.engine.dispose()
    if INST_TEST_DB.exists():
        try: os.remove(INST_TEST_DB)
        except: pass

def test_register_and_deduplicate(inst_service):
    """Verify that registering the same path twice updates the existing record."""
    path = "models/flux_fp16.safetensors"
    
    # 1. First registration
    inst1 = inst_service.register_installation("flux", 1, path)
    assert inst1.model_id == "flux"
    
    # 2. Duplicate registration (different model_id, same path)
    inst2 = inst_service.register_installation("flux_pro", 2, path)
    
    # IDs should match (deduplicated)
    assert inst1.id == inst2.id
    assert inst2.model_id == "flux_pro"

def test_get_installed_with_metadata(inst_service):
    """Verify relational joining of Installation -> Model -> Variant."""
    from src.services.installation_service import db_manager
    session = db_manager.get_session()
    
    # 1. Setup relational data
    m = Model(id="sdxl", name="Stable Diffusion XL", category="image_generation")
    v = ModelVariant(id=1, model_id="sdxl", variant_id="fp16", precision="fp16", vram_min_mb=12000)
    session.add(m)
    session.add(v)
    session.commit()
    
    # 2. Register and complete installation
    inst = inst_service.register_installation("sdxl", 1, "models/sdxl.safetensors")
    inst_service.update_status(inst.id, "installed")
    
    # 3. Query
    results = inst_service.get_installed_models()
    assert len(results) == 1
    
    inst_rec, model_rec, variant_rec = results[0]
    assert model_rec.name == "Stable Diffusion XL"
    assert variant_rec.precision == "fp16"
    assert inst_rec.status == "installed"
    
    session.close()

def test_health_check_missing_file(inst_service):
    """Verify that health check detects missing files."""
    path = "non_existent_file.safetensors"
    inst = inst_service.register_installation("test", 1, path)
    
    # Should be false because file doesn't exist
    is_healthy = inst_service.verify_health(inst.id)
    assert is_healthy is False
    
    # Status should have changed to failed
    from src.services.installation_service import db_manager
    session = db_manager.get_session()
    updated = session.get(Installation, inst.id)
    assert updated.status == "failed"
    session.close()