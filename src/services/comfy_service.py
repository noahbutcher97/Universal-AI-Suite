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
                return file_hash.startswith(expected_hash)
            except Exception as e:
                log.error(f"Hash check failed for {filepath}: {e}")
                return False
        
        return True

    @staticmethod
    def generate_manifest(answers, install_root):
        """
        Generates the installation manifest based on user answers and hardware.
        """
        gpu_name, vram = SystemService.get_gpu_info()
        manifest = []
        res = ComfyService._RES
        
        # 1. Base Installation
        manifest.append({
            "type": "clone", 
            "url": res["core"]["url"], 
            "dest": install_root, 
            "name": "ComfyUI Core"
        })
        manifest.append({
            "type": "clone", 
            "url": res["core"]["manager"], 
            "dest": os.path.join(install_root, "custom_nodes", "ComfyUI-Manager"), 
            "name": "ComfyUI Manager"
        })

        # 2. Model Tier Selection logic
        model_tier = "sd15"
        if vram >= 12: model_tier = "flux"
        elif vram >= 8: model_tier = "sdxl"
        
        ckpt_dir = os.path.join(install_root, "models", "checkpoints")
        
        style = answers.get("style", "General").lower()
        model_data = res["models"].get(style, res["models"]["general"]).get(model_tier)
        
        manifest.append({
            "type": "download", 
            "url": model_data["url"], 
            "dest": ckpt_dir, 
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
