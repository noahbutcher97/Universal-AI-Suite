import shutil
import subprocess
import platform
import sys
import os
from pathlib import Path
from typing import Tuple, Optional
from functools import lru_cache
from src.utils.logger import log
from src.schemas.environment import EnvironmentReport

class SystemService:
    @staticmethod
    @lru_cache(maxsize=1)
    def get_gpu_info() -> Tuple[str, str, float]:
        """
        Detects GPU Name, Vendor, and VRAM. Cached result.
        Returns: (gpu_vendor, gpu_name, vram_gb)
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
                    vram_gb = ram_bytes / (1024**3) # Unified memory is effectively VRAM
                    
                    # Try to get specific chip name
                    chip = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
                    gpu_name = chip
                except Exception as e:
                    log.warning(f"Mac RAM detection failed: {e}")
                    vram_gb = 16.0 # Fallback
                return gpu_vendor, gpu_name, vram_gb

            # 3. AMD/Intel Check (Basic)
            # This is harder to do cross-platform without 3rd party libs like wmi/pyobjc
            # We'll leave as "none" for now unless specific tools are found
            
        except Exception as e:
            log.warning(f"GPU Detection failed: {e}")

        return gpu_vendor, gpu_name, vram_gb

    @staticmethod
    def get_system_ram_gb() -> float:
        """Returns total system RAM in GB."""
        try:
            import psutil
            return psutil.virtual_memory().total / (1024**3)
        except:
            return 8.0

    @staticmethod
    def get_disk_free_gb(path: str = ".") -> int:
        """Returns free disk space at path in GB."""
        try:
            total, used, free = shutil.disk_usage(os.path.abspath(path))
            return int(free / (1024**3))
        except:
            return 0

    @staticmethod
    def detect_form_factor() -> str:
        """
        Detect system form factor (desktop, laptop, mini, workstation).
        """
        if platform.system() == "Windows":
            try:
                # WMI query via PowerShell to avoid `wmi` dependency if possible, 
                # or use ctypes. For now, basic heuristic or assumption.
                # Since we don't have `wmi` in requirements.txt yet, we'll try a PowerShell call.
                cmd = "Get-CimInstance -ClassName Win32_SystemEnclosure | Select-Object -ExpandProperty ChassisTypes"
                output = subprocess.check_output(["powershell", "-Command", cmd], creationflags=subprocess.CREATE_NO_WINDOW).decode().strip()
                # 9, 10, 14 = Laptop
                if any(x in output for x in ["9", "10", "14"]):
                    return "laptop"
            except:
                pass
        
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
        Returns (power_profile, on_battery).
        """
        # Placeholder for complex ctypes logic
        return "balanced", False

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