import os
import platform
import subprocess
from pathlib import Path
from typing import Optional

class ShortcutService:
    """
    Creates OS-appropriate desktop shortcuts/launchers.
    """

    @staticmethod
    def get_desktop_path() -> Path:
        """Returns path to user's Desktop folder."""
        if platform.system() == "Windows":
            return Path(os.path.join(os.environ["USERPROFILE"], "Desktop"))
        else:
            return Path(os.path.join(os.path.expanduser("~"), "Desktop"))

    @staticmethod
    def create_shortcut(
        name: str,
        command: str,
        working_dir: Optional[str] = None,
        icon_path: Optional[str] = None,
        destination: Optional[Path] = None
    ) -> Path:
        """
        Create a desktop shortcut.
        """
        dest = destination or ShortcutService.get_desktop_path()
        
        if platform.system() == "Windows":
            return ShortcutService._create_windows_shortcut(name, command, working_dir, icon_path, dest)
        elif platform.system() == "Darwin":
            return ShortcutService._create_mac_shortcut(name, command, working_dir, icon_path, dest)
        else:
            return ShortcutService._create_linux_shortcut(name, command, working_dir, icon_path, dest)

    @staticmethod
    def _create_windows_shortcut(name, command, working_dir, icon_path, dest_dir):
        # On Windows, we create a .bat file for simplicity without win32com dependency
        # A proper .lnk would require pywin32, which might not be installed yet.
        # Phase 3 enhancement: Use powershell to create real .lnk files.
        shortcut_path = dest_dir / f"{name}.bat"
        
        content = "@echo off\n"
        if working_dir:
            content += f"cd /d \"{working_dir}\"\n"
        content += f"{command}\n"
        content += "pause" # Keep window open if it crashes
        
        with open(shortcut_path, "w") as f:
            f.write(content)
            
        return shortcut_path

    @staticmethod
    def _create_mac_shortcut(name, command, working_dir, icon_path, dest_dir):
        shortcut_path = dest_dir / f"{name}.command"
        
        content = "#!/bin/bash\n"
        if working_dir:
            content += f"cd \"{working_dir}\"\n"
        content += f"{command}\n"
        
        with open(shortcut_path, "w") as f:
            f.write(content)
            
        os.chmod(shortcut_path, 0o755)
        # Remove quarantine
        subprocess.call(["xattr", "-d", "com.apple.quarantine", str(shortcut_path)], stderr=subprocess.DEVNULL)
        return shortcut_path

    @staticmethod
    def _create_linux_shortcut(name, command, working_dir, icon_path, dest_dir):
        shortcut_path = dest_dir / f"{name}.desktop"
        
        content = f"""[Desktop Entry]
Type=Application
Name={name}
Exec=bash -c '{command}; read -p "Press enter to close..."'
Terminal=true
"""
        if working_dir:
            content += f"Path={working_dir}\n"
        if icon_path:
            content += f"Icon={icon_path}\n"
            
        with open(shortcut_path, "w") as f:
            f.write(content)
            
        os.chmod(shortcut_path, 0o755)
        return shortcut_path
