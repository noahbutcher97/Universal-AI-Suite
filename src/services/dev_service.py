import shutil
import platform
import subprocess
import sys
from functools import lru_cache
from src.services.system_service import SystemService
from src.utils.logger import log
from src.config.manager import config_manager

class DevService:
    _RESOURCES = config_manager.get_resources().get("clis", {})
    CLI_MAP = _RESOURCES

    @staticmethod
    @lru_cache(maxsize=32)
    def is_installed(tool_name):
        tool = DevService.CLI_MAP.get(tool_name)
        if not tool: return False
        
        # Check Binary on PATH
        if "bin" in tool and shutil.which(tool["bin"]):
            return True
            
        # Fallback checks (slower)
        if tool["type"] == "npm":
            if not SystemService.check_dependency("NPM", ("npm", "--version")): return False
            try:
                # Check global list
                subprocess.check_call(["npm", "list", "-g", tool["package"], "--depth=0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
                return True
            except: return False
        
        if tool["type"] == "pip":
            pkg = tool["package"]
            cmd = tuple([sys.executable, "-m", "pip", "show", pkg])
            return SystemService.check_dependency(pkg, cmd)
            
        return False

    @staticmethod
    def get_install_cmd(tool_name, scope="user"):
        tool = DevService.CLI_MAP.get(tool_name)
        if not tool: return None
        
        cmd = list(tool["cmd"])
        
        if tool["type"] == "npm":
            if scope == "system": 
                cmd.insert(2, "-g")
            # For user scope in npm, it's default behavior usually, or requires prefix config. 
            # We'll assume default is user/local if not -g.
            
        elif tool["type"] == "pip":
            # Always use current python executable
            cmd = [sys.executable, "-m"] + cmd
            if scope == "user": 
                cmd.append("--user")
                
        return cmd

    @staticmethod
    def clear_cache():
        DevService.is_installed.cache_clear()
