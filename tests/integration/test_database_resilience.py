"""
Database Resilience and Relational Mapping Integrity Tests.
Verifies:
1. Robustness against malformed JSON data.
2. Concurrent session handling.
3. safe_init resilience to schema drift.
"""

import pytest
import sqlite3
import threading
from pathlib import Path
from src.services.model_database import get_model_database, SQLiteModelDatabase
from src.schemas.model import ModelEntry

class TestDatabaseResilience:
    """Tests focused on the robustness of the relational data layer."""

    @pytest.fixture
    def db(self):
        return get_model_database()

    def test_safe_init_schema_drift(self, db):
        """Verify that safe_init ignores extra/unknown JSON keys."""
        # Manually insert a model with "junk" keys in JSON fields
        session = db.db_manager.get_session()
        try:
            from src.services.database.models import Model
            junk_model = Model(
                id="junk_test",
                name="Junk Model",
                category="image_generation",
                capabilities={"scores": {"photorealism": 0.9}, "unknown_new_field": "ignore_me"},
                dependencies={"required_nodes": [], "malformed_key": True},
                explanation={"selected": "Test", "v3_internal_meta": {}},
                cloud={"partner_node": False, "extra_cloud_data": 123},
                hardware={"total_size_gb": 1.0, "new_thermal_metric": 0.5}
            )
            session.merge(junk_model)
            session.commit()
            
            # Attempt to retrieve and map - should NOT crash
            retrieved = db.get_model("junk_test")
            assert retrieved is not None
            assert retrieved.id == "junk_test"
            assert retrieved.capabilities.scores["photorealism"] == 0.9
        finally:
            # Cleanup
            session.query(Model).filter(Model.id == "junk_test").delete()
            session.commit()
            session.close()

    def test_concurrent_read_access(self, db):
        """Verify that multiple threads can read from the DB Singleton simultaneously."""
        errors = []
        def read_loop():
            try:
                for _ in range(50):
                    _ = db.get_all_models()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read_loop) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert len(errors) == 0, f"Concurrent read errors: {errors}"

    def test_missing_nested_fields(self, db):
        """Verify that missing JSON fields result in default-initialized dataclasses."""
        session = db.db_manager.get_session()
        try:
            from src.services.database.models import Model
            minimal_model = Model(
                id="minimal_test",
                name="Minimal",
                category="image_generation",
                capabilities=None, # Missing
                dependencies={},   # Empty
                explanation=None,  # Missing
                cloud=None,
                hardware=None
            )
            session.merge(minimal_model)
            session.commit()
            
            retrieved = db.get_model("minimal_test")
            assert retrieved is not None
            # Should have default-initialized objects, not None
            assert retrieved.capabilities is not None
            assert retrieved.dependencies is not None
            assert retrieved.cloud is not None
            assert retrieved.hardware.total_size_gb == 0.0 # Default value
        finally:
            session.query(Model).filter(Model.id == "minimal_test").delete()
            session.commit()
            session.close()

    def test_invalid_variant_references(self, db):
        """Verify handling of models with no variants."""
        # Should return models even if variants are missing (cloud APIs often have no local variants)
        cloud_models = db.get_cloud_models()
        for m in cloud_models:
            assert isinstance(m, ModelEntry)
            # Cloud models might have empty variants list
            assert isinstance(m.variants, list)
