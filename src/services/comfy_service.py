import os
import hashlib
from src.services.system_service import SystemService
from src.utils.logger import log
from src.config.manager import config_manager

class ComfyService:
    _RES = config_manager.get_resources().get("comfy", {})

    @staticmethod
    def verify_file(filepath, expected_hash=None):
        """
        Verifies file existence and optional hash.
        """
        if not os.path.exists(filepath):
            return False

        if expected_hash:
            # Calculate hash (chunked)
            sha256_hash = hashlib.sha256()
            try:
                with open(filepath, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                file_hash = sha256_hash.hexdigest()
                return file_hash == expected_hash
            except Exception as e:
                log.error(f"Hash check failed for {filepath}: {e}")
                return False

        return True

    @staticmethod
    def generate_manifest(answers, install_root):
        """
        Generates a data-driven installation manifest using RecommendationEngine.
        """
        from src.services.recommendation_service import RecommendationService

        # Get recommendation
        rec = RecommendationService.recommend(answers)
        profile = rec["setup_profile"]
        res = ComfyService._RES
        
        manifest = []

        # 1. Base Installation
        manifest.extend([
            {"type": "clone", "url": res["core"]["url"], "dest": install_root, "name": "ComfyUI Core"},   
            {"type": "clone", "url": res["core"]["manager"], "dest": os.path.join(install_root, "custom_nodes", "ComfyUI-Manager"), "name": "ComfyUI Manager"}
        ])

        # 2. Recommended Model
        base_model = profile.get("base_model")
        if base_model:
            manifest.append({
                "type": "download",
                "url": base_model["url"],
                "dest": os.path.join(install_root, "models", "checkpoints"),
                "name": base_model["name"]
            })

        # 3. Recommended Features (Custom Nodes)
        for feature_key in profile.get("custom_nodes", []):
            feat_config = res["features"].get(feature_key)
            if not feat_config:
                continue
                
            # Install Node
            if "node" in feat_config:
                folder_name = feat_config.get("folder", feature_key)
                manifest.append({
                    "type": "clone",
                    "url": feat_config["node"],
                    "dest": os.path.join(install_root, "custom_nodes", folder_name),
                    "name": f"{feature_key} Node"
                })
            
            # Install Model (if any)
            if "model" in feat_config:
                folder_name = feat_config.get("folder", feature_key)
                
                # Determine destination based on feature type
                dest_path = ""
                if feature_key == "animatediff":
                    dest_path = os.path.join(install_root, "custom_nodes", folder_name, "models")
                elif feature_key == "controlnet":
                    dest_path = os.path.join(install_root, "models", "controlnet")
                
                if dest_path:
                    manifest.append({
                        "type": "download",
                        "url": feat_config["model"],
                        "dest": dest_path,
                        "name": f"{feature_key} Model"
                    })

        return manifest