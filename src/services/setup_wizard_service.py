from typing import List, Dict, Callable, Optional, Any
from pathlib import Path
import subprocess
import os
import sys

from src.schemas.environment import EnvironmentReport
from src.schemas.recommendation import ModuleRecommendation, UserProfile
from src.schemas.installation import InstallationManifest, InstallationItem
from src.services.system_service import SystemService
from src.services.recommendation_service import RecommendationService
from src.services.comfy_service import ComfyService
from src.services.dev_service import DevService
from src.services.download_service import DownloadService
from src.services.shortcut_service import ShortcutService
from src.config.manager import config_manager
from src.utils.logger import log

class SetupWizardService:
    """
    Orchestrates the full setup wizard flow.
    """
    
    def __init__(self):
        self.system_service = SystemService()
        self.recommendation_service = RecommendationService(config_manager.get_resources())
        
        self.env_report: Optional[EnvironmentReport] = None
        self.recommendations: List[ModuleRecommendation] = []
        self.accepted_modules: List[ModuleRecommendation] = []
        
    def start_wizard(self) -> None:
        """Initialize wizard state."""
        self.env_report = None
        self.recommendations = []
        self.accepted_modules = []
        
    def scan_environment(self) -> EnvironmentReport:
        """Run full environment scan."""
        self.env_report = self.system_service.scan_full_environment()
        return self.env_report
        
    def generate_recommendations(self, use_case: str, user_profile: UserProfile) -> List[ModuleRecommendation]:
        """Generate recommendations for selected use case."""
        if not self.env_report:
            raise RuntimeError("Must scan environment first")
            
        self.recommendations = self.recommendation_service.generate_recommendations(
            use_case, self.env_report, user_profile
        )
        return self.recommendations
        
    def accept_module(self, module_id: str, config_overrides: Dict = None) -> None:
        """Mark a module as accepted."""
        # Find recommendation
        rec = next((r for r in self.recommendations if r.module_id == module_id), None)
        if rec:
            if config_overrides:
                rec.config.update(config_overrides)
            self.accepted_modules.append(rec)
            
    def skip_module(self, module_id: str) -> None:
        """Mark a module as skipped."""
        # Just don't add to accepted_modules
        pass
        
    def generate_manifest(self) -> InstallationManifest:
        """Generate unified installation manifest."""
        manifest = InstallationManifest()
        resources = config_manager.get_resources()
        
        for mod in self.accepted_modules:
            if mod.module_id == "comfyui":
                # Get Items
                install_path = config_manager.get("comfy_path")
                items = ComfyService.generate_manifest(mod, install_path)
                manifest.items.extend(items)
                
                # Add Shortcut
                shortcut_tmpl = resources.get("modules", {}).get("comfyui", {}).get("shortcut_templates", {})
                template = shortcut_tmpl.get(sys.platform, shortcut_tmpl.get("windows")) # Default to windows if logic fails? Or linux?
                
                # We need better platform key mapping: 'win32'->'windows', 'darwin'->'darwin', 'linux'->'linux'
                plat_key = "windows" if sys.platform == "win32" else "darwin" if sys.platform == "darwin" else "linux"
                template = shortcut_tmpl.get(plat_key)
                
                if template:
                    # Fill template placeholders
                    cmd = template.replace("{path}", install_path)
                    manifest.shortcuts.append({
                        "name": "ComfyUI Studio",
                        "command": cmd,
                        "icon": "default" # TODO: Icon path
                    })
                    
            elif mod.module_id == "cli_provider":
                provider = mod.config.get("provider")
                install_cmd = DevService.get_install_cmd(provider)
                
                manifest.items.append(InstallationItem(
                    item_id=f"cli_{provider}",
                    item_type="npm" if "npm" in install_cmd[0] else "pip",
                    name=f"{mod.display_name} ({provider})",
                    dest="", # Global or User
                    command=install_cmd
                ))
                
                # Shortcut
                prov_conf = DevService.get_provider_config(provider)
                bin_name = prov_conf.get("bin")
                shortcut_tmpl = resources.get("modules", {}).get("cli_provider", {}).get("shortcut_templates", {})
                plat_key = "windows" if sys.platform == "win32" else "darwin" if sys.platform == "darwin" else "linux"
                template = shortcut_tmpl.get(plat_key)
                
                if template and bin_name:
                    cmd = template.replace("{bin}", bin_name)
                    manifest.shortcuts.append({
                        "name": f"{provider.capitalize()} CLI",
                        "command": cmd,
                        "icon": "default"
                    })
                    
        return manifest
        
    def execute_installation(
        self, 
        manifest: InstallationManifest,
        progress_callback: Callable[[str, float], None],
        error_callback: Callable[[str, Exception], None]
    ) -> bool:
        """Execute the installation manifest."""
        
        total_items = len(manifest.items)
        success = True
        
        for i, item in enumerate(manifest.items):
            try:
                progress_callback(item.name, 0.0)
                
                if item.item_type == "clone":
                    if not os.path.exists(item.dest):
                        os.makedirs(os.path.dirname(item.dest), exist_ok=True)
                        subprocess.check_call(["git", "clone", item.url, item.dest], 
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        # Already exists, maybe pull?
                        pass
                        
                elif item.item_type == "download":
                    os.makedirs(item.dest, exist_ok=True) # Dest is folder in my ComfyService logic, wait.
                    # ComfyService generated item: dest=os.path.join(path, "models", "checkpoints")
                    # But download_file takes full path including filename?
                    # Let's check ComfyService again.
                    # ComfyService: items.append(InstallationItem(..., dest=os.path.join(path, "models", "checkpoints")))
                    # It relies on filename being derived from URL or explicit.
                    # My DownloadService.download_file takes dest_path (file path).
                    
                    # Correction: ComfyService needs to provide FULL file path or we derive it here.
                    # In ComfyService.generate_manifest: 
                    # item.dest was set to DIRECTORY for models.
                    
                    # I need to fix logic here:
                    fname = item.url.split("/")[-1]
                    # Clean query params
                    if "?" in fname: fname = fname.split("?")[0]
                    
                    # If dest is a dir, append fname
                    full_dest = os.path.join(item.dest, fname)
                    if not os.path.exists(item.dest):
                        os.makedirs(item.dest, exist_ok=True)
                        
                    DownloadService.download_file(
                        item.url, 
                        full_dest, 
                        progress_callback=lambda curr, tot: progress_callback(item.name, curr/tot) if tot else None,
                        expected_hash=item.expected_hash
                    )
                    
                elif item.item_type in ["npm", "pip"]:
                    subprocess.check_call(item.command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                progress_callback(item.name, 1.0)
                
            except Exception as e:
                log.error(f"Failed to install {item.name}: {e}")
                error_callback(item.name, e)
                success = False
                
        return success

    def create_shortcuts(self, manifest: InstallationManifest) -> List[Path]:
        """Create desktop shortcuts."""
        paths = []
        for s in manifest.shortcuts:
            try:
                # We need a robust command handling. 
                # ShortcutService.create_shortcut expects "command".
                p = ShortcutService.create_shortcut(
                    name=s["name"],
                    command=s["command"]
                )
                paths.append(p)
            except Exception as e:
                log.error(f"Failed to create shortcut {s['name']}: {e}")
        return paths

    def finalize(self) -> None:
        """Mark wizard as complete."""
        config_manager.set("wizard_completed", True)
        config_manager.set("first_run", False)
