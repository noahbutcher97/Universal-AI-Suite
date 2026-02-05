"""
Integration and regression tests for DB-01: YAML to SQLite Migration.
"""

import pytest
import os
from pathlib import Path
from sqlalchemy import inspect

from src.services.database.models import Base, Model, ModelVariant
from src.services.database.engine import DatabaseManager
from src.services.model_database import SQLiteModelDatabase

# Use a temporary test database
TEST_DB_PATH = Path("data/test_models.db")

@pytest.fixture
def test_db_manager():
    """Provides a clean test database manager."""
    if TEST_DB_PATH.exists():
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass # Handle Windows locked file
    
    manager = DatabaseManager(db_path=TEST_DB_PATH)
    manager.init_db()
    
    yield manager
    
    manager.engine.dispose()
    if TEST_DB_PATH.exists():
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass

def test_database_initialization(test_db_manager):
    """Verify that all tables are created correctly."""
    inspector = inspect(test_db_manager.engine)
    tables = inspector.get_table_names()
    assert "models" in tables
    assert "model_variants" in tables

def test_relational_queries(test_db_manager):
    """Verify that SQLiteModelDatabase provides correct filtering with manual data."""
    session = test_db_manager.get_session()
    
    # 1. Setup Manual Test Data
    m1 = Model(id="test_flux", name="Test Flux", category="image_generation", commercial_use=True)
    v1 = ModelVariant(
        model_id="test_flux", 
        variant_id="fp16", 
        precision="fp16", 
        vram_min_mb=12000, 
        quality_retention_percent=100,
        platform_support={"windows_nvidia": {"supported": True}}
    )
    v2 = ModelVariant(
        model_id="test_flux", 
        variant_id="fp8", 
        precision="fp8", 
        vram_min_mb=8000, 
        quality_retention_percent=98,
        platform_support={"windows_nvidia": {"supported": True, "cc": 8.9}}
    )
    
    session.add(m1)
    session.add(v1)
    session.add(v2)
    session.commit()
    
    sql_db = SQLiteModelDatabase(db_manager=test_db_manager)
    
    # 2. Test VRAM filtering (8GB)
    # Should only return 1 variant (fp8)
    results = sql_db.get_compatible_models(
        platform="windows_nvidia",
        vram_mb=8000,
        categories=["image_generation"],
        compute_capability=8.9
    )
    assert len(results) == 1
    assert results[0][1].variant_id == "fp8"

    # 3. Test CC filtering (CC 7.5)
    # Should return NOTHING because fp8 needs 8.9 and fp16 needs 12GB
    results_low_cc = sql_db.get_compatible_models(
        platform="windows_nvidia",
        vram_mb=8000,
        compute_capability=7.5
    )
    assert len(results_low_cc) == 0

    # 4. Test enough VRAM for fp16
    results_high_vram = sql_db.get_compatible_models(
        platform="windows_nvidia",
        vram_mb=16000
    )
    assert len(results_high_vram) == 1
    # Should pick fp16 as it's higher quality retention
    assert results_high_vram[0][1].variant_id == "fp16"
    
    session.close()
