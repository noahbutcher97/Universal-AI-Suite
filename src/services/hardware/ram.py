"""
RAM detection module per HARDWARE_DETECTION.md Section 5.

Provides RAM detection and offload capacity calculation:
- Total system RAM
- Currently available RAM
- Usable RAM for model layer offloading (conservative calculation)
- System RAM bandwidth detection for offload speed calculation

Phase 1 Week 2a implementation.
"""

import platform
import subprocess
import re
from typing import Optional, Tuple

from src.schemas.hardware import RAMProfile
from src.services.hardware.base import DetectionFailedError
from src.utils.logger import log
from src.utils.subprocess_utils import (
    run_powershell,
    run_command,
    extract_number,
    extract_json,
)
from src.config.constants import OS_RESERVED_RAM_GB, OFFLOAD_SAFETY_FACTOR

# System RAM bandwidth by memory type (GB/s, dual-channel)
# Based on DDR specifications
RAM_BANDWIDTH_GBPS = {
    "ddr5-6400": 102.4,  # 6400 MT/s * 8 bytes * 2 channels / 1000
    "ddr5-6000": 96.0,
    "ddr5-5600": 89.6,
    "ddr5-5200": 83.2,
    "ddr5-4800": 76.8,
    "ddr5": 76.8,        # Default DDR5
    "ddr4-3600": 57.6,
    "ddr4-3200": 51.2,
    "ddr4-2933": 46.9,
    "ddr4-2666": 42.7,
    "ddr4-2400": 38.4,
    "ddr4": 42.7,        # Default DDR4
    "ddr3": 25.6,        # DDR3-1600 dual-channel
    "lpddr5": 68.0,      # Laptop DDR5
    "lpddr4": 34.0,      # Laptop DDR4
}


def detect_ram() -> RAMProfile:
    """
    Detect RAM capacity and calculate offload availability.

    Returns:
        RAMProfile with total, available, and usable_for_offload values

    Raises:
        DetectionFailedError: If RAM detection fails completely

    Example:
        ram = detect_ram()
        if ram.can_offload_model(8.0):
            print("Can offload 8GB model to RAM")

    Note:
        Per SPEC_v3: We must fail explicitly rather than use dangerous
        fallbacks like assuming 16GB RAM.
    """
    total_gb = _get_total_ram()
    available_gb = _get_available_ram()
    usable_for_offload_gb = _calculate_offload_capacity(available_gb)

    # Detect memory type and bandwidth
    memory_type = detect_memory_type()
    bandwidth_gbps = get_bandwidth_for_type(memory_type) if memory_type else None

    return RAMProfile(
        total_gb=total_gb,
        available_gb=available_gb,
        usable_for_offload_gb=usable_for_offload_gb,
        bandwidth_gbps=bandwidth_gbps,
        memory_type=memory_type
    )


def _get_total_ram() -> float:
    """
    Get total system RAM in GB.

    Uses psutil as primary method with platform-specific fallbacks.

    Returns:
        Total RAM in GB

    Raises:
        DetectionFailedError: If all detection methods fail
    """
    # Try psutil first (cross-platform)
    try:
        import psutil
        total_bytes = psutil.virtual_memory().total
        return total_bytes / (1024 ** 3)
    except ImportError:
        log.debug("psutil not available for RAM detection")
    except Exception as e:
        log.debug(f"psutil RAM detection failed: {e}")

    # Platform-specific fallbacks
    system = platform.system()

    if system == "Darwin":
        return _get_total_ram_macos()
    elif system == "Linux":
        return _get_total_ram_linux()
    elif system == "Windows":
        return _get_total_ram_windows()

    # CRITICAL: No fallback - fail explicitly
    raise DetectionFailedError(
        component="RAM",
        message="Could not detect system RAM",
        details=(
            "All detection methods failed. "
            "Install psutil for reliable cross-platform detection."
        )
    )


def _get_total_ram_macos() -> float:
    """Get total RAM on macOS via sysctl."""
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            mem_bytes = int(result.stdout.strip())
            return mem_bytes / (1024 ** 3)
    except Exception as e:
        log.debug(f"macOS sysctl RAM detection failed: {e}")

    raise DetectionFailedError(
        component="RAM",
        message="Could not detect RAM on macOS",
        details="sysctl hw.memsize failed"
    )


def _get_total_ram_linux() -> float:
    """Get total RAM on Linux via /proc/meminfo."""
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    # Value is in kB
                    kb = int(line.split()[1])
                    return kb / (1024 ** 2)
    except Exception as e:
        log.debug(f"Linux /proc/meminfo RAM detection failed: {e}")

    raise DetectionFailedError(
        component="RAM",
        message="Could not detect RAM on Linux",
        details="/proc/meminfo parsing failed"
    )


def _get_total_ram_windows() -> float:
    """Get total RAM on Windows via PowerShell or wmic."""
    # Try PowerShell first (uses shared utilities per ARCHITECTURE_PRINCIPLES.md)
    output = run_powershell(
        "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"
    )
    mem_bytes = extract_number(output)
    if mem_bytes:
        return mem_bytes / (1024 ** 3)

    # Try wmic as fallback
    try:
        creation_flags = subprocess.CREATE_NO_WINDOW
        result = subprocess.run(
            ["wmic", "ComputerSystem", "get", "TotalPhysicalMemory"],
            capture_output=True,
            text=True,
            creationflags=creation_flags,
            timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                mem_bytes = int(lines[1].strip())
                return mem_bytes / (1024 ** 3)
    except Exception as e:
        log.debug(f"wmic RAM detection failed: {e}")

    raise DetectionFailedError(
        component="RAM",
        message="Could not detect RAM on Windows",
        details="Both PowerShell and wmic failed"
    )


def _get_available_ram() -> float:
    """
    Get currently available RAM in GB.

    Available RAM = memory that can be allocated without swapping.

    Returns:
        Available RAM in GB, or 80% of total if detection fails
    """
    try:
        import psutil
        available_bytes = psutil.virtual_memory().available
        return available_bytes / (1024 ** 3)
    except ImportError:
        log.debug("psutil not available for available RAM detection")
    except Exception as e:
        log.debug(f"psutil available RAM detection failed: {e}")

    # Fallback: Estimate 80% of total as available
    # This is conservative for idle systems
    try:
        total = _get_total_ram()
        return total * 0.8
    except Exception:
        # If even total fails, return 0 (safe)
        return 0.0


def _calculate_offload_capacity(available_gb: float) -> float:
    """
    Calculate usable RAM for model layer offloading.

    Per HARDWARE_DETECTION.md Section 5.4:
    - Conservative formula: (available - 4GB) * 0.8
    - Leaves 4GB for OS and other applications
    - Uses 80% of remainder as safety margin

    Args:
        available_gb: Currently available RAM in GB

    Returns:
        Usable RAM for offload in GB (minimum 0)
    """
    usable = (available_gb - OS_RESERVED_RAM_GB) * OFFLOAD_SAFETY_FACTOR

    # Never return negative
    return max(0.0, usable)


def calculate_offload_viability(
    vram_gb: float,
    ram_profile: RAMProfile,
    cpu_can_offload: bool,
    gpu_bandwidth_gbps: Optional[float] = None,
) -> dict:
    """
    Calculate effective capacity with CPU offload.

    Per HARDWARE_DETECTION.md Section 5.4:
    - Offload viable if CPU tier is HIGH or MEDIUM
    - Adds usable RAM to VRAM for effective capacity
    - Speed ratio calculated from actual memory bandwidth

    Uses encapsulated lookup pattern per ARCHITECTURE_PRINCIPLES.md:
    - RAM bandwidth is read from ram_profile.bandwidth_gbps (detected during RAM detection)
    - GPU bandwidth should be passed from HardwareProfile.gpu_bandwidth_gbps

    Args:
        vram_gb: Available GPU VRAM in GB
        ram_profile: RAMProfile with offload capacity and bandwidth
        cpu_can_offload: Whether CPU tier supports offload
        gpu_bandwidth_gbps: GPU memory bandwidth in GB/s (optional, from HardwareProfile)

    Returns:
        Dict with offload metrics:
        - gpu_only_gb: Capacity without offload
        - with_offload_gb: Capacity with offload
        - offload_viable: Boolean if offload is possible
        - speed_ratio: Ratio of offload speed to GPU speed (bandwidth-based, or None if unknown)

    Example:
        # With full HardwareProfile (preferred - encapsulated):
        result = calculate_offload_viability(
            vram_gb=profile.vram_gb,
            ram_profile=profile.ram,
            cpu_can_offload=profile.cpu.tier in (CPUTier.HIGH, CPUTier.MEDIUM),
            gpu_bandwidth_gbps=profile.gpu_bandwidth_gbps,
        )

        # Or with standalone RAMProfile:
        result = calculate_offload_viability(
            vram_gb=24.0,
            ram_profile=ram_profile,  # Has bandwidth_gbps from detect_ram()
            cpu_can_offload=True,
            gpu_bandwidth_gbps=1008.0,  # RTX 4090
        )
    """
    gpu_only = vram_gb

    # Get RAM bandwidth from profile (encapsulated lookup)
    ram_bandwidth_gbps = ram_profile.bandwidth_gbps or 0.0

    if cpu_can_offload and ram_profile.usable_for_offload_gb > OS_RESERVED_RAM_GB:
        with_offload = vram_gb + ram_profile.usable_for_offload_gb
        offload_viable = True

        # Calculate speed ratio from actual bandwidth if available
        # Formula: speed_ratio = ram_bandwidth / gpu_bandwidth
        # Example: DDR5 (80 GB/s) / GDDR6X (1000 GB/s) = 0.08
        if gpu_bandwidth_gbps and gpu_bandwidth_gbps > 0 and ram_bandwidth_gbps > 0:
            speed_ratio = ram_bandwidth_gbps / gpu_bandwidth_gbps
        else:
            # Cannot calculate without bandwidth data
            speed_ratio = None
    else:
        with_offload = vram_gb
        offload_viable = False
        speed_ratio = 1.0  # No offload, full GPU speed

    return {
        "gpu_only_gb": gpu_only,
        "with_offload_gb": with_offload,
        "offload_viable": offload_viable,
        "speed_ratio": speed_ratio,
    }


def detect_memory_type() -> Optional[str]:
    """
    Detect system RAM type (DDR4, DDR5, LPDDR5, etc.).

    Uses platform-specific methods:
    - Windows: PowerShell Get-WmiObject (SMBIOSMemoryType field)
    - macOS: system_profiler SPMemoryDataType
    - Linux: dmidecode (requires sudo) or /sys/devices

    Returns:
        Memory type string (e.g., "ddr5", "ddr4", "lpddr5") or None if unknown

    Note:
        Detection may fail without elevated privileges on some platforms.
        Returns normalized lowercase string for lookup in RAM_BANDWIDTH_GBPS.
    """
    system = platform.system()

    if system == "Windows":
        return _detect_memory_type_windows()
    elif system == "Darwin":
        return _detect_memory_type_macos()
    elif system == "Linux":
        return _detect_memory_type_linux()

    return None


def _detect_memory_type_windows() -> Optional[str]:
    """
    Detect memory type on Windows via PowerShell/WMI.

    SMBIOSMemoryType values:
    - 26 = DDR4
    - 34 = DDR5
    - 27 = LPDDR4
    - 35 = LPDDR5
    """
    # Query memory type via WMI (uses shared utilities per ARCHITECTURE_PRINCIPLES.md)
    ps_script = '''
$mem = Get-WmiObject Win32_PhysicalMemory | Select-Object -First 1
$speed = $mem.ConfiguredClockSpeed
$type = $mem.SMBIOSMemoryType
@{Type=$type; Speed=$speed} | ConvertTo-Json
'''
    output = run_powershell(ps_script)
    data = extract_json(output)

    if not data:
        return None

    smbios_type = data.get("Type")
    speed = data.get("Speed")

    # Map SMBIOSMemoryType to DDR generation
    type_map = {
        26: "ddr4",
        34: "ddr5",
        27: "lpddr4",
        35: "lpddr5",
        24: "ddr3",
    }

    base_type = type_map.get(smbios_type)
    if base_type and speed:
        # Include speed for more precise bandwidth lookup
        # e.g., "ddr5-6400" or "ddr4-3200"
        speed_key = f"{base_type}-{speed}"
        if speed_key in RAM_BANDWIDTH_GBPS:
            return speed_key
        return base_type

    return base_type


def _detect_memory_type_macos() -> Optional[str]:
    """
    Detect memory type on macOS.

    Apple Silicon uses unified memory (LPDDR5 on M3/M4, LPDDR4X on M1/M2).
    Intel Macs may have DDR4 or DDR3.
    """
    try:
        # Check if Apple Silicon
        if platform.machine() == "arm64":
            # Apple Silicon uses LPDDR5 (M3/M4) or LPDDR4X (M1/M2)
            # Detect chip to determine memory type
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=5
            )
            chip_info = result.stdout.strip().lower() if result.returncode == 0 else ""

            # M3 and M4 use LPDDR5
            if "m3" in chip_info or "m4" in chip_info:
                return "lpddr5"
            # M1 and M2 use LPDDR4X (similar to LPDDR5 for our purposes)
            return "lpddr4"

        # Intel Mac - check system_profiler
        result = subprocess.run(
            ["system_profiler", "SPMemoryDataType"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            output = result.stdout.lower()
            if "ddr5" in output:
                return "ddr5"
            elif "ddr4" in output:
                return "ddr4"
            elif "ddr3" in output:
                return "ddr3"

    except Exception as e:
        log.debug(f"macOS memory type detection failed: {e}")

    return None


def _detect_memory_type_linux() -> Optional[str]:
    """
    Detect memory type on Linux via /sys or dmidecode.

    Falls back to heuristics based on memory speed if type not available.
    """
    try:
        # Try reading from /sys/devices/system/memory
        # This path may contain memory type info on some systems
        # Alternative: Parse /proc/meminfo for hints

        # Try dmidecode (requires root, but may work via sudo)
        result = subprocess.run(
            ["dmidecode", "-t", "memory"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            output = result.stdout.lower()
            # Look for Type field
            for line in output.split('\n'):
                if 'type:' in line and 'error' not in line:
                    if 'ddr5' in line:
                        return "ddr5"
                    elif 'ddr4' in line:
                        return "ddr4"
                    elif 'ddr3' in line:
                        return "ddr3"
                    elif 'lpddr5' in line:
                        return "lpddr5"
                    elif 'lpddr4' in line:
                        return "lpddr4"

                # Also check for speed to determine generation
                if 'speed:' in line:
                    # Parse speed in MT/s
                    speed_match = re.search(r'(\d+)\s*(mt/s|mhz)', line)
                    if speed_match:
                        speed = int(speed_match.group(1))
                        # DDR5 typically 4800+ MT/s
                        # DDR4 typically 2133-3600 MT/s
                        if speed >= 4800:
                            return "ddr5"
                        elif speed >= 2133:
                            return "ddr4"
                        else:
                            return "ddr3"

    except FileNotFoundError:
        log.debug("dmidecode not found, trying alternative detection")
    except Exception as e:
        log.debug(f"Linux dmidecode detection failed: {e}")

    # Fallback: Assume DDR4 as most common for desktop Linux
    # This is a reasonable default for 2020+ systems
    log.debug("Could not detect memory type on Linux, bandwidth will be unavailable")
    return None


def get_bandwidth_for_type(memory_type: Optional[str]) -> Optional[float]:
    """
    Get memory bandwidth in GB/s for a given memory type.

    Uses the RAM_BANDWIDTH_GBPS lookup table with known DDR specifications.

    Args:
        memory_type: Memory type string (e.g., "ddr5", "ddr4-3200")

    Returns:
        Bandwidth in GB/s, or None if type unknown

    Note:
        Bandwidth values assume dual-channel configuration.
        Single-channel systems will have half the listed bandwidth.
    """
    if memory_type is None:
        return None

    # Normalize to lowercase
    type_key = memory_type.lower()

    # Direct lookup
    if type_key in RAM_BANDWIDTH_GBPS:
        return RAM_BANDWIDTH_GBPS[type_key]

    # Try base type without speed suffix
    base_type = type_key.split('-')[0]
    if base_type in RAM_BANDWIDTH_GBPS:
        return RAM_BANDWIDTH_GBPS[base_type]

    log.debug(f"No bandwidth data for memory type: {memory_type}")
    return None
