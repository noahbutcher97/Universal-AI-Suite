"""
System service for environment detection and dependency checking.

MIGRATION NOTE (Phase 1):
The GPU detection in get_gpu_info() now delegates to the new platform-specific
detectors in src/services/hardware/. The old implementation is preserved below
for reference but no longer executes.

See: docs/spec/MIGRATION_PROTOCOL.md Section 3
"""

import shutil
import subprocess
import platform
import sys
import os
from pathlib import Path
from typing import Tuple, Optional, Dict
from functools import lru_cache
from src.utils.logger import log
from src.schemas.environment import EnvironmentReport

# Feature flag for new hardware detection (Pattern C from migration protocol)
USE_NEW_HARDWARE_DETECTION = True


class SystemService:
    @staticmethod
    @lru_cache(maxsize=1)
    def get_gpu_info() -> Tuple[str, str, float]:
        """
        Detects GPU Name, Vendor, and VRAM. Cached result.
        Returns: (gpu_vendor, gpu_name, vram_gb)

        .. deprecated::
            This method now delegates to src/services/hardware/ detectors.
            For full hardware profile, use:
                from src.services.hardware import detect_hardware
                profile = detect_hardware()

            This function will be simplified in v1.0.
            See: docs/spec/MIGRATION_PROTOCOL.md Section 3
        """
        if USE_NEW_HARDWARE_DETECTION:
            # NEW: Delegate to platform-specific detectors
            # Per SPEC_v3 Section 4 and MIGRATION_PROTOCOL Pattern B
            from src.services.hardware import get_legacy_gpu_info
            return get_legacy_gpu_info()

        # OLD implementation preserved for rollback (Pattern C toggle)
        # This code path is disabled by default
        return _legacy_get_gpu_info()

    @staticmethod
    def get_system_ram_gb() -> Optional[float]:
        """
        Returns total system RAM in GB.

        Returns: RAM in GB, or None if detection fails.

        Per ARCHITECTURE_PRINCIPLES: Explicit failure, no silent fallbacks.
        """
        try:
            import psutil
            return psutil.virtual_memory().total / (1024**3)
        except ImportError:
            log.error("psutil not installed - cannot detect RAM")
            return None
        except Exception as e:
            log.error(f"RAM detection failed: {e}")
            return None

    @staticmethod
    def get_disk_free_gb(path: str = ".") -> Optional[float]:
        """
        Returns free disk space at path in GB.

        Returns: Free space in GB, or None if detection fails.

        Per ARCHITECTURE_PRINCIPLES: Explicit failure, no silent fallbacks.
        """
        try:
            total, used, free = shutil.disk_usage(os.path.abspath(path))
            return free / (1024**3)
        except FileNotFoundError:
            log.error(f"Path not found for disk check: {path}")
            return None
        except Exception as e:
            log.error(f"Disk space detection failed: {e}")
            return None

    @staticmethod
    def get_required_headroom_gb() -> float:
        """
        Calculate recommended storage headroom to maintain OS stability.

        Formula: (System_RAM * 0.5) + STORAGE_SAFETY_BUFFER_GB
        - System_RAM * 0.5 accounts for potential large swap file / paging needs
        - Buffer for OS updates, hibernation file, and temp files

        Per Task SYS-05.
        """
        from src.config.constants import STORAGE_SAFETY_BUFFER_GB
        ram_gb = SystemService.get_system_ram_gb() or 16.0
        return (ram_gb * 0.5) + STORAGE_SAFETY_BUFFER_GB

    @staticmethod
    def check_storage_headroom(required_gb: float, path: str = ".") -> bool:
        """
        Check if an installation can proceed while maintaining recommended headroom.

        Returns: True if there is enough space + headroom.
        """
        free_gb = SystemService.get_disk_free_gb(path)
        if free_gb is None:
            return False

        headroom = SystemService.get_required_headroom_gb()
        return (free_gb - headroom) >= required_gb

    @staticmethod
    def detect_form_factor() -> str:
        """
        Detect system form factor (desktop, laptop, mini, workstation).

        Per ARCHITECTURE_PRINCIPLES: Uses run_powershell() with -NoProfile.
        """
        if platform.system() == "Windows":
            try:
                from src.utils.subprocess_utils import run_powershell

                cmd = "Get-CimInstance -ClassName Win32_SystemEnclosure | Select-Object -ExpandProperty ChassisTypes"
                output = run_powershell(cmd, timeout=10)

                if output:
                    # ChassisTypes: 9, 10, 14 = Laptop/Notebook/Sub-Notebook
                    if any(x in output for x in ["9", "10", "14"]):
                        return "laptop"
            except ImportError:
                log.warning("subprocess_utils not available, using fallback")
                # Fallback to direct call if utilities not available
                try:
                    cmd = "Get-CimInstance -ClassName Win32_SystemEnclosure | Select-Object -ExpandProperty ChassisTypes"
                    output = subprocess.check_output(
                        ["powershell", "-NoProfile", "-Command", cmd],
                        creationflags=subprocess.CREATE_NO_WINDOW
                    ).decode().strip()
                    if any(x in output for x in ["9", "10", "14"]):
                        return "laptop"
                except Exception:
                    pass
            except Exception as e:
                log.warning(f"Form factor detection failed: {e}")

        # Default to desktop if detection fails
        return "desktop"

    @staticmethod
    def detect_storage_type(path: str = ".") -> str:
        """
        Detect storage type (NVMe, SATA SSD, HDD).
        """
        # Very platform specific. Returning generic for now to be safe.
        # Can implement the specific `df` or `wmi` logic from specs later
        # once we add `wmi` to requirements.
        return "unknown"

    @staticmethod
    def detect_power_state() -> Tuple[str, bool]:
        """
        Detect current power state and profile.

        Returns: (power_profile, on_battery)
            - power_profile: "high_performance", "balanced", "power_saver", "unknown"
            - on_battery: True if running on battery, False if plugged in

        Per SPEC §4.6: Platform-specific power detection.
        """
        system = platform.system()

        if system == "Windows":
            return SystemService._detect_power_state_windows()
        elif system == "Darwin":
            return SystemService._detect_power_state_macos()
        elif system == "Linux":
            return SystemService._detect_power_state_linux()
        else:
            return "unknown", False

    @staticmethod
    def _detect_power_state_windows() -> Tuple[str, bool]:
        """Windows power state detection via GetSystemPowerStatus."""
        try:
            import ctypes
            from ctypes import wintypes

            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", ctypes.c_byte),
                    ("BatteryFlag", ctypes.c_byte),
                    ("BatteryLifePercent", ctypes.c_byte),
                    ("SystemStatusFlag", ctypes.c_byte),
                    ("BatteryLifeTime", wintypes.DWORD),
                    ("BatteryFullLifeTime", wintypes.DWORD),
                ]

            status = SYSTEM_POWER_STATUS()
            if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                log.warning("GetSystemPowerStatus failed")
                return "unknown", False

            # ACLineStatus: 0 = offline (battery), 1 = online (plugged in), 255 = unknown
            on_battery = status.ACLineStatus == 0

            # Try to detect power profile via powercfg
            try:
                from src.utils.subprocess_utils import run_powershell
                output = run_powershell("powercfg /getactivescheme", timeout=5)
                if output:
                    output_lower = output.lower()
                    if "high performance" in output_lower:
                        return "high_performance", on_battery
                    elif "power saver" in output_lower:
                        return "power_saver", on_battery
                    elif "balanced" in output_lower:
                        return "balanced", on_battery
            except Exception:
                pass

            return "balanced", on_battery

        except Exception as e:
            log.warning(f"Windows power state detection failed: {e}")
            return "unknown", False

    @staticmethod
    def _detect_power_state_macos() -> Tuple[str, bool]:
        """macOS power state detection via pmset."""
        try:
            result = subprocess.run(
                ["pmset", "-g", "batt"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return "unknown", False

            output = result.stdout.lower()

            # Check power source
            on_battery = "battery power" in output or "'battery power'" in output
            on_ac = "ac power" in output or "'ac power'" in output

            if on_ac:
                on_battery = False
            elif not on_battery and not on_ac:
                # Default to plugged in if unclear
                on_battery = False

            # macOS doesn't have explicit power profiles like Windows
            # Detect if Low Power Mode is enabled
            try:
                lpm_result = subprocess.run(
                    ["pmset", "-g"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "lowpowermode" in lpm_result.stdout.lower() and "1" in lpm_result.stdout:
                    return "power_saver", on_battery
            except Exception:
                pass

            return "balanced", on_battery

        except subprocess.TimeoutExpired:
            log.warning("pmset power check timed out")
            return "unknown", False
        except FileNotFoundError:
            return "unknown", False
        except Exception as e:
            log.warning(f"macOS power state detection failed: {e}")
            return "unknown", False

    @staticmethod
    def _detect_power_state_linux() -> Tuple[str, bool]:
        """Linux power state detection via /sys/class/power_supply."""
        try:
            import os

            power_supply_path = "/sys/class/power_supply"
            on_battery = True  # Default to battery if no AC found

            if os.path.exists(power_supply_path):
                for supply in os.listdir(power_supply_path):
                    supply_path = os.path.join(power_supply_path, supply)
                    type_path = os.path.join(supply_path, "type")
                    online_path = os.path.join(supply_path, "online")

                    if os.path.exists(type_path):
                        with open(type_path, 'r') as f:
                            supply_type = f.read().strip().lower()

                        # Check if AC adapter is online
                        if supply_type in ("mains", "usb"):
                            if os.path.exists(online_path):
                                with open(online_path, 'r') as f:
                                    online = f.read().strip()
                                    if online == "1":
                                        on_battery = False
                                        break

            # Linux power profiles (if available)
            profile = "balanced"
            try:
                # Check power-profiles-daemon (GNOME)
                result = subprocess.run(
                    ["powerprofilesctl", "get"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    profile_output = result.stdout.strip().lower()
                    if "performance" in profile_output:
                        profile = "high_performance"
                    elif "power-saver" in profile_output:
                        profile = "power_saver"
                    elif "balanced" in profile_output:
                        profile = "balanced"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

            return profile, on_battery

        except Exception as e:
            log.warning(f"Linux power state detection failed: {e}")
            return "unknown", False

    @staticmethod
    def get_running_processes(names: list[str]) -> list[dict]:
        """
        Returns a list of running processes matching the given names (case-insensitive).
        Returns: [{'pid': int, 'name': str}, ...]
        """
        matches = []
        names_lower = [n.lower() for n in names]
        
        if platform.system() == "Windows":
            try:
                # Use CSV format for easier parsing
                output = subprocess.check_output(
                    ["tasklist", "/FO", "CSV"], 
                    creationflags=subprocess.CREATE_NO_WINDOW
                ).decode(errors='ignore')
                
                import csv
                import io
                reader = csv.reader(io.StringIO(output))
                next(reader, None) # Skip header
                
                for row in reader:
                    if len(row) >= 2:
                        pname = row[0]
                        pid = row[1]
                        if pname.lower() in names_lower:
                            matches.append({'pid': int(pid), 'name': pname})
            except Exception as e:
                log.warning(f"Process check failed: {e}")
        
        return matches

    @staticmethod
    def kill_processes(process_list: list[dict]) -> bool:
        """
        Terminates the specified processes.
        """
        if platform.system() != "Windows":
            return False
            
        success = True
        for p in process_list:
            try:
                subprocess.check_call(
                    ["taskkill", "/F", "/PID", str(p['pid'])],
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                success = False
        return success

    @staticmethod
    def ensure_no_locks(tool_id: str, confirmation_callback=None) -> bool:
        """
        Generic helper to check for and kill locking processes for a given tool.
        Returns True if safe to proceed, False if cancelled.
        """
        if platform.system() != "Windows":
            return True
            
        # Map tool IDs to typical locking process names
        lock_map = {
            "winget": ["winget.exe", "AppInstaller.exe"],
            "docker": ["docker.exe", "Docker Desktop.exe", "com.docker.backend.exe"],
            "node": ["node.exe"],
            "npm": ["node.exe"],
            "python": ["python.exe", "pythonw.exe"],
            "git": ["git.exe"],
            "ollama": ["ollama.exe", "ollama_llama_server.exe"]
        }
        
        # Check standard and provided ID
        names = lock_map.get(tool_id.lower(), [f"{tool_id}.exe"])
        
        running = SystemService.get_running_processes(names)
        if running:
            if confirmation_callback:
                if confirmation_callback(running):
                    return SystemService.kill_processes(running)
                else:
                    return False
            else:
                log.warning(f"Locks found for {tool_id}: {running}. No callback provided. Proceeding with caution.")
        
        return True

    @staticmethod
    def install_winget(confirmation_callback=None) -> bool:
        """
        Attempts to install Winget (App Installer) on Windows.
        Returns True if successful (or already present), False otherwise.
        
        Args:
            confirmation_callback: A function(processes) -> bool that asks user to kill processes.
        """
        if platform.system() != "Windows":
            return False
            
        # 1. Check existing (PATH)
        if shutil.which("winget"):
            return True

        # 2. Check existing (Standard Location) - Avoid reinstall if just missing from PATH
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        winget_path_dir = os.path.join(local_app_data, "Microsoft", "WindowsApps")
        winget_exe = os.path.join(winget_path_dir, "winget.exe")
        
        if os.path.exists(winget_exe):
            log.info(f"Winget found at {winget_exe} (missing from PATH). Patching...")
            new_path = f"{os.environ['PATH']}{os.pathsep}{winget_path_dir}"
            os.environ["PATH"] = new_path
            
            # Persist to User PATH
            try:
                ps_cmd = f'[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";{winget_path_dir}", "User")'
                subprocess.check_call(["powershell", "-NoProfile", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                log.warning(f"Failed to persist Winget to PATH: {e}")

            if shutil.which("winget"):
                log.info("Winget path patched and verified successfully.")
                return True
            else:
                log.warning("Winget path patched but 'winget' command still not found.")
            
        log.info("Attempting to install Winget...")
        
        # 3. Check for conflicts
        if not SystemService.ensure_no_locks("winget", confirmation_callback):
            log.warning("User cancelled Winget install due to locking processes.")
            return False

        # Latest Stable Release
        url = "https://github.com/microsoft/winget-cli/releases/download/v1.9.25180/Microsoft.DesktopAppInstaller_8wekyb3d8bbwe.msixbundle"
        import uuid
        dest = os.path.join(os.environ["TEMP"], f"winget_{uuid.uuid4().hex[:8]}.msixbundle")
        
        try:
            import requests
            import time
            
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(dest, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            log.info(f"Winget bundle downloaded to {dest}. Installing...")
            
            # Use ForceUpdateFromAnyVersion to handle re-installs/upgrades
            cmd = f"Add-AppxPackage -Path '{dest}' -ForceUpdateFromAnyVersion"
            subprocess.check_call(
                ["powershell", "-NoProfile", "-Command", cmd]
            )
            
            log.info("Installation command finished. Verifying...")

            # 4. Path Patching & Polling
            # Poll for file existence (up to 15s)
            for _ in range(15):
                if os.path.exists(winget_exe):
                    break
                time.sleep(1)
            
            # Patch PATH if found but not detected
            if os.path.exists(winget_exe) and not shutil.which("winget"):
                log.info(f"Winget found at {winget_exe}, adding to PATH...")
                os.environ["PATH"] += os.pathsep + winget_path_dir
                
            # Final Check
            if shutil.which("winget"):
                log.info("Winget detected successfully.")
                return True
            else:
                log.warning("Winget installed but not found in PATH.")
                return False
            
        except Exception as e:
            log.error(f"Failed to install Winget: {e}")
            return False
        finally:
            # Cleanup
            if os.path.exists(dest):
                try:
                    os.remove(dest)
                except:
                    pass

    @staticmethod
    def scan_full_environment() -> EnvironmentReport:
        """
        Comprehensive environment scan.
        """
        gpu_vendor, gpu_name, vram_gb = SystemService.get_gpu_info()
        ram_gb = SystemService.get_system_ram_gb()
        disk_free = SystemService.get_disk_free_gb()

        # Software checks
        git_ok = SystemService.check_dependency("Git", ("git", "--version"))
        node_ok = SystemService.check_dependency("Node", ("node", "--version"))
        npm_ok = SystemService.check_dependency("NPM", ("npm", "--version"))

        return EnvironmentReport(
            os_name=platform.system(),
            os_version=platform.release(),
            arch=platform.machine(),
            gpu_vendor=gpu_vendor,
            gpu_name=gpu_name,
            vram_gb=vram_gb,
            ram_gb=ram_gb,
            disk_free_gb=disk_free,

            form_factor=SystemService.detect_form_factor(),

            python_version=sys.version.split()[0],
            git_installed=git_ok,
            node_installed=node_ok,
            npm_installed=npm_ok,

            # TODO: Add logic to find existing ComfyUI
            comfyui_path=None
        )

    @staticmethod
    @lru_cache(maxsize=32)
    def check_dependency(name, check_cmd_tuple):
        """
        Checks if a tool is installed.
        """
        try:
            subprocess.check_call(
                check_cmd_tuple,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=(platform.system()=="Windows")
            )
            return True
        except:
            return False

    @staticmethod
    def verify_environment() -> Dict[str, bool]:
        """Quick check for Overview Frame."""
        return {
            "git": SystemService.check_dependency("Git", ("git", "--version")),
            "node": SystemService.check_dependency("Node", ("node", "--version")),
            "npm": SystemService.check_dependency("NPM", ("npm", "--version"))
        }


# Legacy implementation moved outside class for rollback purposes
def _legacy_get_gpu_info() -> Tuple[str, str, float]:
    """
    Legacy GPU detection implementation.

    DEPRECATED: This function is kept for rollback purposes only.
    Do not use directly - use SystemService.get_gpu_info() instead.

    Known issues (per SPEC_v3 audit):
    - Falls back to 16GB on Apple Silicon detection error (CRITICAL)
    - No 75% memory ceiling for Apple Silicon
    - No CUDA compute capability detection
    - No AMD ROCm support
    """
    gpu_vendor = "none"
    gpu_name = "CPU (Slow)"
    vram_gb = 0.0

    try:
        # 1. NVIDIA Check
        if shutil.which("nvidia-smi"):
            try:
                output = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                    creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
                ).decode()
                name, mem = output.strip().split(',')
                gpu_vendor = "nvidia"
                gpu_name = name
                vram_gb = float(mem) / 1024
                return gpu_vendor, gpu_name, vram_gb
            except Exception as e:
                log.warning(f"NVIDIA detection failed: {e}")

        # 2. Apple Silicon Check
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            gpu_vendor = "apple"
            gpu_name = "Apple Silicon (MPS)"
            try:
                # Get unified memory size
                result = subprocess.check_output(["sysctl", "-n", "hw.memsize"])
                ram_bytes = int(result.strip())
                # BUG: Should apply 75% ceiling, but keeping for backwards compat
                vram_gb = ram_bytes / (1024**3)

                # Try to get specific chip name
                chip = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
                gpu_name = chip
            except Exception as e:
                log.warning(f"Mac RAM detection failed: {e}")
                # BUG: 16GB fallback causes wrong recommendations
                # This is why we migrated to new detectors
                vram_gb = 16.0
            return gpu_vendor, gpu_name, vram_gb

        # 3. AMD/Intel Check (Basic)
        # This is harder to do cross-platform without 3rd party libs like wmi/pyobjc
        # We'll leave as "none" for now unless specific tools are found

    except Exception as e:
        log.warning(f"GPU Detection failed: {e}")

    return gpu_vendor, gpu_name, vram_gb
