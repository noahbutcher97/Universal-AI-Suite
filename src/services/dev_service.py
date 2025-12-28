import shutil
import platform
import subprocess
import sys
from functools import lru_cache
from src.services.system_service import SystemService
from src.utils.logger import log
from src.config.manager import config_manager

class DevService:
    """A service for managing developer command-line interface (CLI) tools."""
    _RESOURCES = config_manager.get_resources().get("clis", {})
    CLI_MAP = _RESOURCES

    @staticmethod
    @lru_cache(maxsize=32)
    def is_installed(tool_name):
        """
        Checks if a CLI tool is installed. Results are cached.

        Args:
            tool_name (str): The name of the tool to check (e.g., "Claude CLI").

        Returns:
            bool: True if the tool is found, False otherwise.
        """
        tool = DevService.CLI_MAP.get(tool_name)
        if not tool: return False
        
        # Check Binary on PATH (fastest)
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
        """
        Constructs the installation command for a given tool.

        Args:
            tool_name (str): The name of the tool.
            scope (str): 'user' for local install, 'system' for global.

        Returns:
            list: A list of command arguments for subprocess, or None.
        """
        tool = DevService.CLI_MAP.get(tool_name)
        if not tool: return None
        
        cmd = list(tool["cmd"])
        
        if tool["type"] == "npm":
            if scope == "system": 
                cmd.insert(2, "-g")
            # For user scope in npm, it's default behavior.
            
        elif tool["type"] == "pip":
            # Always use current python executable
            cmd = [sys.executable, "-m"] + cmd
            if scope == "user": 
                cmd.append("--user")
                
        return cmd

    # #TODO: Implement uninstall functionality for CLI tools.
    # The service layer should provide a method to generate uninstall commands,
    # complementing the existing install functionality. This is essential for
    # complete lifecycle management of the tools.
    #
    # Suggested implementation:
    # 1. Create a new static method `get_uninstall_cmd(tool_name, scope)`.
    # 2. In this method, look up the tool in `CLI_MAP`.
    # 3. Based on the tool's type (`npm` or `pip`), construct the uninstall
    #    command. For example:
    #    - npm: `['npm', 'uninstall', '-g', tool['package']]`
    #    - pip: `[sys.executable, '-m', 'pip', 'uninstall', '-y', tool['package']]`
    # 4. The UI layer will call this method to get the command and then execute
    #    it in a separate thread.

    @staticmethod
    def clear_cache():
        """Clears the cache for is_installed checks."""
        DevService.is_installed.cache_clear()
