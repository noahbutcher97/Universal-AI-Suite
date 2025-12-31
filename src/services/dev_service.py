import shutil
import platform
import subprocess
import sys
import os
from typing import List, Optional
from functools import lru_cache
from src.services.system_service import SystemService
from src.utils.logger import log
from src.config.manager import config_manager

class DevService:
    """A service for managing developer command-line interface (CLI) tools."""
    
    @property
    def _providers(self):
        return config_manager.get_resources().get("modules", {}).get("cli_provider", {}).get("providers", {})

    @staticmethod
    def get_provider_config(provider_name: str) -> Optional[dict]:
        resources = config_manager.get_resources()
        return resources.get("modules", {}).get("cli_provider", {}).get("providers", {}).get(provider_name)

    @staticmethod
    def is_installed(provider_name: str) -> bool:
        """
        Checks if a CLI tool is installed.
        """
        tool = DevService.get_provider_config(provider_name)
        if not tool: return False
        
        # Check Binary on PATH
        if "bin" in tool and shutil.which(tool["bin"]):
            return True
            
        # Fallback checks
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
            
        return False

    @staticmethod
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
            if scope == "system" or True: # Force global for CLIs usually
                cmd.insert(2, "-g")
            return cmd
            
        elif pkg_type == "pip":
            cmd = [sys.executable, "-m", "pip", "install", pkg]
            if scope == "user": 
                cmd.append("--user")
            return cmd
                
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
            
        return []

    @staticmethod
    def validate_api_key(provider: str, api_key: str) -> bool:
        """
        Validate an API key by making a minimal API call.
        """
        # This implementation requires specific logic per provider.
        # For prototype, we might just check length or basic format.
        # Ideally, we make a curl request.
        
        if not api_key:
            return False
            
        if provider == "gemini":
            # Simple check or call models.list
            try:
                import requests
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                response = requests.get(url, timeout=5)
                return response.status_code == 200
            except:
                return False
                
        elif provider == "claude":
            # Anthropic check
            try:
                import requests
                url = "https://api.anthropic.com/v1/models"
                headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
                response = requests.get(url, headers=headers, timeout=5)
                return response.status_code == 200
            except:
                return False
                
        return True # Default to True if we can't check, assuming user knows best

    @staticmethod
    def get_binary_path(provider_name: str) -> Optional[str]:
        """Get full path to installed CLI binary."""
        tool = DevService.get_provider_config(provider_name)
        if not tool: return None
        return shutil.which(tool.get("bin"))