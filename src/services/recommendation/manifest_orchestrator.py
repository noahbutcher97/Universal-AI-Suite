"""
Manifest Orchestrator.
Task: Intelligent dependency-aware manifest generation.

Takes high-level model choices and use cases, then resolves all 
cascading dependencies (VAE, nodes, encoders, adapters) to build
 a complete InstallationManifest.
"""

from typing import List, Dict, Any, Optional, Set
from src.schemas.installation import InstallationManifest, InstallationItem
from src.schemas.recommendation import UserProfile
from src.services.recommendation.topsis_layer import RankedCandidate
from src.services.model_database import SQLiteModelDatabase, ModelEntry, ModelVariant
from src.utils.logger import log

class ManifestOrchestrator:
    """
    Orchestrates the creation of a complete installation manifest.
    Handles recursive dependency resolution.
    """
    
    def __init__(self, model_db: Optional[SQLiteModelDatabase] = None):
        from src.services.model_database import get_model_database
        self.model_db = model_db or get_model_database()
        self._processed_ids: Set[str] = set()

    def create_manifest(
        self, 
        recommendations: List[RankedCandidate], 
        user_profile: UserProfile
    ) -> InstallationManifest:
        """
        Builds a full manifest from recommendations.
        """
        manifest = InstallationManifest()
        self._processed_ids.clear()
        
        all_items: List[InstallationItem] = []
        
        # 1. Process primary recommendations
        for ranked in recommendations:
            candidate = ranked.scored_candidate.passing_candidate
            model = candidate.model
            variant = candidate.variant
            
            # Resolve dependencies for this model+variant
            items = self.resolve_dependencies(model, variant)
            for item in items:
                if item.item_id not in self._processed_ids:
                    all_items.append(item)
                    self._processed_ids.add(item.item_id)

        manifest.items = all_items
        self._calculate_summary(manifest)
        
        return manifest

    def resolve_dependencies(self, model: ModelEntry, variant: ModelVariant) -> List[InstallationItem]:
        """
        Recursively finds all required components for a model variant.
        """
        items = []
        
        # 1. The Model itself
        items.append(InstallationItem(
            item_id=f"model_{model.id}_{variant.id}",
            item_type="download",
            name=f"{model.name} ({variant.precision})",
            dest=f"models/checkpoints/{model.id}_{variant.id}.safetensors",
            url=variant.download_url,
            expected_hash=variant.sha256,
            size_bytes=int(variant.download_size_gb * 1024 * 1024 * 1024)
        ))

        # 2. Resolve VAE (Architecture awareness)
        vae_id = model.architecture.get("vae")
        if vae_id:
            vae_item = self._get_vae_item(vae_id)
            if vae_item: items.append(vae_item)

        # 3. Resolve Custom Nodes (from variant and model)
        node_ids = set(variant.requires_nodes)
        # Check model-level dependencies
        for dep_node in model.dependencies.required_nodes:
            if isinstance(dep_node, str):
                node_ids.add(dep_node)
            elif isinstance(dep_node, dict):
                node_ids.add(dep_node.get("package", ""))

        for node_id in node_ids:
            if not node_id: continue
            node_item = self._get_node_item(node_id)
            if node_item: items.append(node_item)

        # 4. Resolve Secondary Encoders/Adapters (future)
        
        return items

    def _get_vae_item(self, vae_id: str) -> Optional[InstallationItem]:
        # Search DB for this VAE
        # In a real impl, VAEs are just entries in models_database.yaml under 'vaes' or 'text_encoders'
        # For now, we'll scaffold a few common ones
        vae_map = {
            "sd_vae": {
                "name": "SDXL VAE (Fixed)",
                "url": "https://huggingface.co/madebyollin/sdxl-vae-fp16-fix/resolve/main/sdxl_vae.safetensors",
                "dest": "models/vae/sdxl_vae.safetensors",
                "size": 0.35
            }
        }
        
        data = vae_map.get(vae_id)
        if not data: return None
        
        return InstallationItem(
            item_id=f"vae_{vae_id}",
            item_type="download",
            name=data["name"],
            dest=data["dest"],
            url=data["url"],
            size_bytes=int(data["size"] * 1024 * 1024 * 1024)
        )

    def _get_node_item(self, node_id: str) -> Optional[InstallationItem]:
        """Convert a node ID to an InstallationItem (Git clone)."""
        # Look up node in local_models.custom_nodes
        # This logic will use self.model_db once custom_nodes are indexed
        return InstallationItem(
            item_id=f"node_{node_id}",
            item_type="clone",
            name=f"Custom Node: {node_id}",
            dest=f"custom_nodes/{node_id}",
            url=f"https://github.com/example/{node_id}" # Placeholder
        )

    def _calculate_summary(self, manifest: InstallationManifest):
        total_bytes = sum(item.size_bytes for item in manifest.items if item.size_bytes)
        manifest.total_size_gb = total_bytes / (1024**3)
        manifest.estimated_time_minutes = int(manifest.total_size_gb * 5) # Assume 200MB/min avg
