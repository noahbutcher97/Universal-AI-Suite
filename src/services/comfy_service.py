import os
import shutil
import hashlib
from typing import List, Dict, Any
from pathlib import Path
from src.schemas.recommendation import ModuleRecommendation
from src.schemas.installation import InstallationItem
from src.config.manager import config_manager
from src.utils.logger import log

class ComfyService:
    
    @staticmethod
    def generate_manifest(
        recommendation: ModuleRecommendation,
        install_path: str
    ) -> List[InstallationItem]:
        """
        Generate installation items from recommendation.
        V2 Implementation.
        """
        items = []
        resources = config_manager.get_resources()
        comfy_res = resources.get("modules", {}).get("comfyui", {})
        
        # 1. ComfyUI Core
        core_repo = comfy_res.get("core", {}).get("repo")
        if core_repo:
            items.append(InstallationItem(
                item_id="comfy_core",
                item_type="clone",
                name="ComfyUI Core",
                url=core_repo,
                dest=install_path
            ))
            
        # 2. ComfyUI Manager
        manager_repo = comfy_res.get("core", {}).get("manager_repo")
        if manager_repo:
            items.append(InstallationItem(
                item_id="comfy_manager",
                item_type="clone",
                name="ComfyUI Manager",
                url=manager_repo,
                dest=os.path.join(install_path, "custom_nodes", "ComfyUI-Manager")
            ))
            
        # 3. Custom Nodes
        required_nodes = recommendation.config.get("required_nodes", [])
        custom_nodes_res = resources.get("comfyui_components", {}).get("custom_nodes", {})
        
        for node_key in required_nodes:
            # Skip manager if listed (already added)
            if node_key == "ComfyUI-Manager":
                continue
                
            node_def = custom_nodes_res.get(node_key)
            if node_def:
                items.append(InstallationItem(
                    item_id=f"node_{node_key}",
                    item_type="clone",
                    name=node_def.get("display_name", node_key),
                    url=node_def.get("repo"),
                    dest=os.path.join(install_path, node_def.get("dest_folder", f"custom_nodes/{node_key}"))
                ))
                
        # 4. Models
        # Checkpoint
        model_name = recommendation.config.get("selected_model")
        model_url = recommendation.config.get("selected_model_url")
        if model_name and model_url:
             items.append(InstallationItem(
                item_id="model_checkpoint",
                item_type="download",
                name=f"Model: {model_name}",
                url=model_url,
                dest=os.path.join(install_path, "models", "checkpoints"),
                # We could look up hash/size from resources if we iterate candidates again
                # For now rely on simple config
            ))
             
        return items

    @staticmethod
    def generate_v1_manifest(answers, install_root):
        """
        Legacy V1 manifest generation. Kept for backward compatibility.
        """
        # ... (Old implementation would go here if needed, but for now we focus on V2)
        # We can implement a bridge if strictly required.
        pass

    @staticmethod
    def install_custom_node(node_url: str, dest_path: str) -> bool:
        """Clone a custom node repository."""
        # Implementation depends on execution environment.
        # This might just check if it exists or return a manifest item?
        # The spec implies an action.
        try:
            import subprocess
            subprocess.check_call(["git", "clone", node_url, dest_path])
            return True
        except Exception as e:
            log.error(f"Failed to install custom node: {e}")
            return False

    @staticmethod
    def deploy_workflow(
        workflow_key: str, 
        comfy_path: str,
        resources: dict
    ) -> bool:
        """
        Copy workflow template to ComfyUI workflows directory.
        """
        workflows = resources.get("comfyui_components", {}).get("workflows", {})
        wf_def = workflows.get(workflow_key)
        
        if not wf_def:
            log.error(f"Workflow {workflow_key} not found definition")
            return False
            
        src_file = wf_def.get("file") # Relative to app root
        # Assuming app root is CWD or known
        # We need a robust way to find 'src' or 'workflows' dir
        # For now assume CWD/workflows/...
        
        src_path = os.path.abspath(src_file)
        if not os.path.exists(src_path):
             # Try relative to src?
             src_path = os.path.abspath(os.path.join("src", src_file))
             
        if not os.path.exists(src_path):
            log.error(f"Workflow source file not found: {src_path}")
            return False
            
        dest_dir = os.path.join(comfy_path, "user", "default", "workflows")
        os.makedirs(dest_dir, exist_ok=True)
        
        try:
            shutil.copy(src_path, dest_dir)
            return True
        except Exception as e:
             log.error(f"Failed to copy workflow: {e}")
             return False

    @staticmethod
    def validate_installation(comfy_path: str) -> Dict[str, bool]:
        """
        Validate ComfyUI installation.
        """
        path = Path(comfy_path)
        return {
            "core_exists": (path / "main.py").exists(),
            "venv_exists": (path / "venv").exists() or (path / ".dashboard_env").exists(), # Check typical venv spots
            "manager_exists": (path / "custom_nodes" / "ComfyUI-Manager").exists(),
            "can_launch": (path / "main.py").exists() # Simplistic for now
        }

    @staticmethod
    def get_installed_models(comfy_path: str) -> Dict[str, List[str]]:
        """
        List installed models by category.
        """
        path = Path(comfy_path)
        models_dir = path / "models"
        result = {}
        
        if not models_dir.exists():
            return result
            
        for category in ["checkpoints", "unet", "loras", "vae", "controlnet"]:
            cat_dir = models_dir / category
            if cat_dir.exists():
                # List files recursively or just top level? Comfy supports subfolders.
                files = [f.name for f in cat_dir.glob("**/*") if f.is_file() and f.suffix in {'.safetensors', '.ckpt', '.gguf', '.pth'}]
                result[category] = files
            else:
                result[category] = []
                
        return result
    
    @staticmethod
    def verify_file(filepath, expected_hash=None):
        """
        Verifies file existence and optional hash.
        """
        if not os.path.exists(filepath):
            return False

        if expected_hash:
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
