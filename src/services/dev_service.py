import shutil
import platform
import subprocess
import sys
import os
from typing import List, Optional, Dict, Any
from functools import lru_cache
from src.services.system_service import SystemService
from src.utils.logger import log
from src.config.manager import config_manager

class DevService:
    """A service for managing developer command-line interface (CLI) tools."""
    
    @staticmethod
    @lru_cache
    def get_system_tools_config() -> Dict:
        return config_manager.get_resources().get("system_tools", {})

    @staticmethod
    def get_system_tool_def(tool_id: str) -> Optional[Dict]:
        return DevService.get_system_tools_config().get("definitions", {}).get(tool_id)

    @staticmethod
    def check_system_tool(tool_id: str) -> bool:
        """Check if a system tool is installed (via PATH)."""
        tool = DevService.get_system_tool_def(tool_id)
        if not tool: return False
        
        # Special check for Chocolatey/Scoop (PowerShell functions, not always binaries)
        if tool_id in ["chocolatey", "scoop"] and platform.system() == "Windows":
            # Simple check if command runs
            try:
                subprocess.check_call(["powershell", "-c", f"{tool['bin']} --version"], 
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except:
                return False

        return bool(shutil.which(tool.get("bin")))

    @staticmethod
    @lru_cache
    def get_system_install_cmd(tool_id: str) -> Any:
        """Get install command (List or String) for current OS."""
        tool = DevService.get_system_tool_def(tool_id)
        if not tool: return None
        
        os_key = platform.system().lower() # windows, darwin, linux
        cmd = tool.get("install", {}).get(os_key)
        
        # Fallback for Linux if not specified (manual)
        if not cmd and os_key == "linux":
            return None
            
        return cmd

    @property
    def _providers(self):
        # Migrated: CLI providers now come from the relational database
        from src.services.model_database import get_model_database
        db = get_model_database()
        return {m.id: m for m in db.get_models_by_category("cli_provider")}

    @staticmethod
    def get_all_providers() -> List[str]:
        """Returns a list of all available CLI provider keys."""
        from src.services.model_database import get_model_database
        db = get_model_database()
        return [m.id for m in db.get_models_by_category("cli_provider")]

    @staticmethod
    @lru_cache
    def get_provider_config(provider_name: str) -> Optional[dict]:
        """Get provider configuration from model database."""
        from src.services.model_database import get_model_database
        db = get_model_database()
        model = db.get_model(provider_name)
        if not model: return None
        
        # Convert ModelEntry to dict for compatibility
        return {
            "display_name": model.name,
            "package": model.dependencies.package,
            "package_type": model.dependencies.package_type,
            "bin": model.dependencies.bin,
            "api_key_name": model.dependencies.api_key_name
        }

    @staticmethod
    def is_installed(provider_name: str) -> bool:
        """
        Checks if a CLI tool is installed.
        Optimized: If 'bin' is defined, rely on shutil.which (fast).
        """
        tool = DevService.get_provider_config(provider_name)
        if not tool: return False
        
        # Fast Path: Binary Check
        if tool.get("bin") and shutil.which(tool["bin"]):
            return True
            
        # Slow Path: Package Manager Checks (Fallback if binary missing but package installed)
        pkg_type = tool.get("package_type")
        pkg = tool.get("package")
        
        if pkg_type == "npm":
            if not SystemService.check_dependency("NPM", ("npm", "--version")): return False
            try:
                subprocess.check_call(["npm", "list", "-g", pkg, "--depth=0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                return True
            except: return False
        
        if pkg_type == "pip":
            cmd = tuple([sys.executable, "-m", "pip", "show", pkg])
            return SystemService.check_dependency(pkg, cmd)
            
        if pkg_type == "system":
            return False # Should have had 'bin' defined

        return False

    @staticmethod
    @lru_cache
    def get_install_cmd(provider_name: str, scope="user") -> List[str]:
        """
        Constructs the installation command for a given tool.
        """
        tool = DevService.get_provider_config(provider_name)
        if not tool: return []
        
        pkg = tool.get("package")
        pkg_type = tool.get("package_type")
        
        if pkg_type == "npm":
            cmd = ["npm", "install", pkg]
            if scope == "system":
                cmd.insert(2, "-g")
            return cmd
            
        elif pkg_type == "pip":
            cmd = [sys.executable, "-m", "pip", "install", pkg]
            
            # Check if running in venv
            in_venv = (sys.prefix != sys.base_prefix)
            
            # Only add --user if NOT in venv and scope is user
            if scope == "user" and not in_venv: 
                cmd.append("--user")
            return cmd
        
        elif pkg_type == "system":
            system = platform.system()
            
            if system == "Windows":
                if shutil.which("winget"):
                    return ["winget", "install", "-e", "--id", pkg, "--source", "winget"]
                else:
                    log.warning("Winget not found.")
                    return []
            
            elif system == "Darwin":
                if shutil.which("brew"):
                    # Map 'Ollama.Ollama' (Winget ID) to 'ollama' (Brew formula)
                    brew_pkg = "ollama" if "ollama" in pkg.lower() else pkg.lower()
                    return ["brew", "install", brew_pkg]
                else:
                    log.warning("Homebrew not found.")
                    return []
            
            elif system == "Linux":
                # Special handling for Ollama (Script install)
                if "ollama" in pkg.lower():
                    return ["curl -fsSL https://ollama.com/install.sh | sh"]
                
                # Generic Linux (apt/dnf is hard to predict without user input/sudo)
                # Fallback to manual
                return []
                
        return []

    @staticmethod
    def get_uninstall_cmd(provider_name: str, scope="user") -> List[str]:
        """
        Get uninstall command for a CLI tool.
        """
        tool = DevService.get_provider_config(provider_name)
        if not tool: return []

        pkg = tool.get("package")
        pkg_type = tool.get("package_type")
        
        if pkg_type == "npm":
            cmd = ["npm", "uninstall", pkg]
            if scope == "system" or True:
                cmd.insert(2, "-g")
            return cmd
            
        elif pkg_type == "pip":
            return [sys.executable, "-m", "pip", "uninstall", "-y", pkg]
        
        elif pkg_type == "system":
            if platform.system() == "Windows":
                return ["winget", "uninstall", "--id", pkg]
            
        return []

    @staticmethod
    def validate_api_key(provider: str, api_key: str) -> bool:
        """
        Validate an API key by making a minimal API call.
        """
        if not api_key:
            return False
            
        if provider == "gemini":
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                response = requests.get(url, timeout=5)
                return response.status_code == 200
            except:
                return False
                
        elif provider == "claude":
            try:
                import requests
                url = "https://api.anthropic.com/v1/models"
                headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
                response = requests.get(url, headers=headers, timeout=5)
                return response.status_code == 200
            except:
                return False
                
        return True 

    @staticmethod
    def get_binary_path(provider_name: str) -> Optional[str]:
        """Get full path to installed CLI binary."""
        tool = DevService.get_provider_config(provider_name)
        if not tool: return None
        return shutil.which(tool.get("bin"))
    
    @staticmethod
    def add_to_system_path(tool_name: str) -> bool:
        """
        Adds the tool's binary directory to the User PATH (Windows only for now).
        """
        if platform.system() != "Windows":
            return False

        tool_conf = DevService.get_provider_config(tool_name)
        if not tool_conf: return False

        try:
            pkg_type = tool_conf.get("package_type")
            target_path = None
            
            if pkg_type == "npm":
                target_path = os.path.join(os.getenv('APPDATA'), 'npm')
            elif pkg_type == "pip":
                # If running in venv, adding venv/Scripts to PATH is what makes it "global"
                if os.environ.get("VIRTUAL_ENV"):
                    target_path = os.path.join(os.environ["VIRTUAL_ENV"], "Scripts")
                else:
                    # User Install location
                    target_path = os.path.join(os.getenv('APPDATA'), 'Python', 'Python311', 'Scripts')
            
            if target_path and os.path.exists(target_path):
                # Verify not already in PATH (case-insensitive check)
                current_path = os.environ.get("PATH", "")
                if target_path.lower() not in current_path.lower():
                    log.info(f"Adding {target_path} to User PATH...")
                    
                    # Append to User Path via PowerShell
                    ps_cmd = f'[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";{target_path}", "User")'
                    subprocess.check_call(
                        ["powershell", "-NoProfile", "-Command", ps_cmd], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL
                    )
                    
                    # Update local env for current session
                    os.environ["PATH"] += f";{target_path}"
                    return True
                else:
                    log.info(f"{target_path} already in PATH.")
                    return True # Already done is a success
            else:
                log.warning(f"Target path {target_path} does not exist.")
                return False
                
        except Exception as e:
            log.error(f"Failed to update PATH for {tool_name}: {e}")
            return False

    @staticmethod
    def clear_cache():
        """Clears any caches."""
        SystemService.check_dependency.cache_clear()
