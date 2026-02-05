"""
Synchronization script to migrate data from models_database.yaml to SQLite.
Part of Task DB-01.
"""

import sys
import os
from pathlib import Path

# Add project root to path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from src.services.model_database import ModelDatabase
from src.services.database.engine import db_manager
from src.services.database.models import Model, ModelVariant
from src.utils.logger import log

def sync_yaml_to_db(custom_manager=None):
    """
    Reads the YAML database and populates the SQLite tables.
    """
    log.info("Starting YAML to SQLite synchronization...")
    
    # 1. Initialize DB
    active_manager = custom_manager or db_manager
    active_manager.init_db()
    session = active_manager.get_session()
    
    # 2. Load YAML
    model_db = ModelDatabase()
    if not model_db.load():
        log.error("Failed to load YAML source.")
        return

    try:
        # Clear existing data (v1 simplification)
        session.query(ModelVariant).delete()
        session.query(Model).delete()
        session.commit()
        
        count = 0
        # Iterate through models in ModelDatabase
        # Using ModelDatabase's internal parser results
        for model_id, entry in model_db._models.items():
            # Create Model record
            db_model = Model(
                id=entry.id,
                name=entry.name,
                family=entry.family,
                release_date=entry.release_date,
                license=entry.license,
                commercial_use=entry.commercial_use,
                category=entry.category,
                description=entry.description,
                repository_url=entry.repository_url,
                is_cloud_api=entry.is_cloud_api,
                provider=entry.provider,
                # JSON fields
                architecture=entry.architecture if hasattr(entry, 'architecture') else {},
                capabilities={
                    "primary": entry.capabilities.primary,
                    "scores": entry.capabilities.scores,
                    "features": entry.capabilities.features,
                    "style_strengths": entry.capabilities.style_strengths
                },
                dependencies={
                    "required_nodes": entry.dependencies.required_nodes,
                    "paired_models": entry.dependencies.paired_models,
                    "package": entry.dependencies.package,
                    "package_type": entry.dependencies.package_type,
                    "bin": entry.dependencies.bin,
                    "api_key_name": entry.dependencies.api_key_name,
                    "api_key_url": entry.dependencies.api_key_url
                },
                explanation={
                    "selected": entry.explanation.selected,
                    "rejected_vram": entry.explanation.rejected_vram,
                    "rejected_platform": entry.explanation.rejected_platform
                },
                cloud={
                    "partner_node": entry.cloud.partner_node,
                    "partner_service": entry.cloud.partner_service,
                    "replicate": entry.cloud.replicate
                },
                hardware={
                    "total_size_gb": entry.hardware.total_size_gb,
                    "compute_intensity": entry.hardware.compute_intensity,
                    "supports_cpu_offload": entry.hardware.supports_cpu_offload
                },
                pricing=entry.pricing
            )
            session.add(db_model)
            
            # Create Variants
            for v in entry.variants:
                db_variant = ModelVariant(
                    model_id=entry.id,
                    variant_id=v.id,
                    precision=v.precision,
                    vram_min_mb=v.vram_min_mb,
                    vram_recommended_mb=v.vram_recommended_mb,
                    download_size_gb=v.download_size_gb,
                    quality_retention_percent=v.quality_retention_percent,
                    download_url=v.download_url,
                    sha256=v.sha256,
                    platform_support={
                        p: {"supported": ps.supported, "cc": ps.min_compute_capability}
                        for p, ps in v.platform_support.items()
                    },
                    requires_nodes=v.requires_nodes,
                    notes=v.notes
                )
                session.add(db_variant)
            
            count += 1
            if count % 10 == 0:
                session.flush()

        session.commit()
        log.info(f"Successfully synced {count} models to SQLite.")

    except Exception as e:
        session.rollback()
        log.error(f"Sync failed: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    sync_yaml_to_db()
