"""
Installation Service.
Part of Task DB-03: Relational Installation Tracking.

Manages the lifecycle of local model and component installations.
"""

import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.services.database.engine import db_manager
from src.services.database.models import Installation, Model, ModelVariant
from src.utils.logger import log

class InstallationService:
    """
    Handles tracking, querying, and verifying local installations.
    """
    
    def __init__(self):
        db_manager.init_db()

    def register_installation(
        self,
        model_id: str,
        variant_db_id: int,
        local_path: str,
        item_type: str = "model",
        metadata: Optional[Dict] = None
    ) -> Installation:
        """
        Creates or updates an installation record.
        Ensures path deduplication.
        """
        session = db_manager.get_session()
        try:
            # Normalize path
            abs_path = os.path.abspath(local_path)
            
            # Check for existing installation at this path
            existing = session.query(Installation).filter_by(local_path=abs_path).first()
            
            if existing:
                log.info(f"Updating existing installation record at: {abs_path}")
                existing.status = "pending"
                existing.model_id = model_id
                existing.variant_db_id = variant_db_id
                existing.metadata_json = metadata or {}
                session.commit()
                session.refresh(existing)
                session.expunge(existing)
                return existing

            # Create new record
            new_inst = Installation(
                model_id=model_id,
                variant_db_id=variant_db_id,
                local_path=abs_path,
                item_type=item_type,
                status="pending",
                metadata_json=metadata or {}
            )
            session.add(new_inst)
            session.commit()
            session.refresh(new_inst)
            session.expunge(new_inst)
            log.info(f"Registered new {item_type} installation: {model_id}")
            return new_inst
        finally:
            session.close()

    def update_status(self, installation_id: int, status: str, current_bytes: int = 0, total_bytes: int = 0):
        """Update the progress or final status of an installation."""
        session = db_manager.get_session()
        try:
            inst = session.get(Installation, installation_id)
            if inst:
                inst.status = status
                if current_bytes: inst.current_bytes = current_bytes
                if total_bytes: inst.total_bytes = total_bytes
                
                if status == "installed":
                    inst.installed_at = datetime.utcnow()
                    inst.checksum_verified = True
                
                session.commit()
        finally:
            session.close()

    def get_installed_models(self) -> List[tuple[Installation, Model, ModelVariant]]:
        """
        Returns all successfully installed models with their metadata.
        """
        session = db_manager.get_session()
        try:
            results = session.query(Installation, Model, ModelVariant).join(
                Model, Installation.model_id == Model.id
            ).join(
                ModelVariant, Installation.variant_db_id == ModelVariant.id
            ).filter(Installation.status == "installed").all()
            return results
        finally:
            session.close()

    def verify_health(self, installation_id: int) -> bool:
        """
        Check if the file still exists and optionally verify hash.
        """
        session = db_manager.get_session()
        try:
            inst = session.get(Installation, installation_id)
            if not inst or not inst.local_path:
                return False
            
            # 1. Physical existence check
            if not os.path.exists(inst.local_path):
                log.warning(f"Health check failed: File missing at {inst.local_path}")
                inst.status = "failed"
                session.commit()
                return False
            
            # 2. Hash verification (deferred to PAT-03 or background worker)
            inst.last_verified_at = datetime.utcnow()
            session.commit()
            return True
        finally:
            session.close()
