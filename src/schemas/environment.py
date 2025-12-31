from dataclasses import dataclass
from typing import List, Optional

@dataclass
class EnvironmentReport:
    """Output of SystemService.scan_full_environment()"""

    # Hardware
    os_name: str                    # "Windows", "Darwin", "Linux"
    os_version: str                 # e.g., "10.0.19041", "14.1.2"
    arch: str                       # "x86_64", "arm64"
    gpu_vendor: str                 # "nvidia", "apple", "amd", "none"
    gpu_name: str                   # "NVIDIA GeForce RTX 3080"
    vram_gb: float                  # 10.0
    ram_gb: float                   # 64.0
    disk_free_gb: int               # 250

    # Extended Hardware (New in V2)
    gpu_memory_bandwidth_gbps: Optional[float] = None
    cuda_compute_capability: Optional[str] = None
    tensor_cores: bool = False
    multi_gpu: bool = False
    gpu_count: int = 1
    
    cpu_name: str = "Unknown"
    cpu_vendor: str = "unknown"
    cpu_cores_physical: int = 4
    cpu_cores_logical: int = 8
    cpu_frequency_ghz: float = 2.5
    cpu_architecture: str = "x86_64"
    
    ram_type: str = "Unknown"
    ram_speed_mhz: Optional[int] = None
    memory_bandwidth_gbps: Optional[float] = None
    unified_memory: bool = False
    
    disk_total_gb: float = 0.0
    storage_type: str = "unknown" # "nvme", "sata_ssd", "hdd", "unknown"
    storage_read_speed_mbps: Optional[float] = None
    
    form_factor: str = "desktop" # "desktop", "laptop", "mini", "workstation"
    power_profile: str = "balanced"
    tdp_watts: Optional[int] = None
    cooling_capacity: str = "medium"
    on_battery: bool = False

    # Software
    python_version: str = "3.10"
    git_installed: bool = False
    node_installed: bool = False
    npm_installed: bool = False

    # Existing Installations
    comfyui_path: Optional[str] = None
    comfyui_version: Optional[str] = None
    lm_studio_installed: bool = False

    # Derived
    hardware_profile: str = "unknown"
    recommended_model_tier: str = "sd15"
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
