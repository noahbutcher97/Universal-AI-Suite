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
            # #TODO: Enhance file verification to handle missing hashes gracefully.
            # If a file exists but no hash is provided in resources.json,
            # the file is considered verified. This is a potential gap.
            #
            # Suggested implementation:
            # 1. Log a warning when a file is verified without a hash check.
            #    `log.warn(f"No hash provided for {filepath}. Skipping integrity check.")`
            # 2. Add a 'strict' mode parameter to the function. In strict mode,
            #    if a hash is missing, the verification should fail. This would be
            #    useful for ensuring all production assets are verifiable.

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
        Generates a data-driven installation manifest.
        """
        _, vram = SystemService.get_gpu_info()
        manifest = []
        res = ComfyService._RES
        
        # 1. Base Installation
        manifest.extend([
            {"type": "clone", "url": res["core"]["url"], "dest": install_root, "name": "ComfyUI Core"},
            {"type": "clone", "url": res["core"]["manager"], "dest": os.path.join(install_root, "custom_nodes", "ComfyUI-Manager"), "name": "ComfyUI Manager"}
        ])

        # 2. Data-Driven Model Tier Selection
        model_tier = "sd15" # Default
        for tier, reqs in res["model_tiers"].items():
            if vram >= reqs["min_vram"]:
                model_tier = tier
                break # First match wins (highest VRAM)
        
        style = answers.get("style", "General").lower()
        model_data = res["models"].get(style, res["models"]["general"]).get(model_tier)
        
        # #TODO: Make manifest generation more resilient to missing configuration.
        # If `model_data` is None because of a misconfiguration in resources.json
        # (e.g., a missing model for a specific style and tier), the installation
        # will proceed without a base model, which will cause ComfyUI to fail.
        #
        # Suggested implementation:
        # 1. Check if `model_data` is None.
        # 2. If it is, log an error and either raise an exception that the UI
        #    can catch and display, or gracefully fall back to a default
        #    model (like the "general" "sd15" model) and log a warning.

        if model_data:
            manifest.append({
                "type": "download",
                "url": model_data["url"],
                "dest": os.path.join(install_root, "models", "checkpoints"),
                "name": model_data["name"]
            })

        # 3. Feature Selection
        if answers.get("media") in ["Video", "Mixed"]:
            feat = res["features"]["animatediff"]
            manifest.append({
                "type": "clone", "url": feat["node"], 
                "dest": os.path.join(install_root, "custom_nodes", "ComfyUI-AnimateDiff-Evolved"), 
                "name": "AnimateDiff Node"
            })
            manifest.append({
                "type": "download", "url": feat["model"], 
                "dest": os.path.join(install_root, "custom_nodes", "ComfyUI-AnimateDiff-Evolved", "models"), 
                "name": "AnimateDiff V2 Motion Model"
            })

        if answers.get("consistency"):
            manifest.append({
                "type": "clone", "url": res["features"]["ipadapter"], 
                "dest": os.path.join(install_root, "custom_nodes", "ComfyUI_IPAdapter_plus"), 
                "name": "IPAdapter Plus"
            })
            
        if answers.get("editing"):
            feat = res["features"]["controlnet"]
            manifest.append({
                "type": "clone", "url": feat["node"], 
                "dest": os.path.join(install_root, "custom_nodes", "comfyui_controlnet_aux"), 
                "name": "ControlNet Preprocessors"
            })
            manifest.append({
                "type": "download", "url": feat["model"], 
                "dest": os.path.join(install_root, "models", "controlnet"), 
                "name": "ControlNet Canny (SD1.5)"
            })

        return manifest
