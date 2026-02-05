"""
Hardware Adapter for Recommendation Engine.
Part of Task PAT-04: Environment to HardwareProfile Adapter.

Translates the legacy EnvironmentReport (from scan) into the modern
HardwareProfile required by the 3-layer recommendation engine.
"""

from src.schemas.environment import EnvironmentReport
from src.schemas.hardware import (
    HardwareProfile, 
    PlatformType, 
    CPUProfile, 
    CPUTier, 
    RAMProfile, 
    StorageProfile, 
    StorageTier,
    FormFactorProfile
)

class HardwareAdapter:
    """Adapts EnvironmentReport to HardwareProfile."""

    @staticmethod
    def to_profile(env: EnvironmentReport) -> HardwareProfile:
        """
        Transform legacy scan results into a rich hardware profile.
        """
        # 1. Map Platform
        os_name = env.os_name.lower()
        if "windows" in os_name:
            plat = PlatformType.WINDOWS_NVIDIA
        elif "darwin" in os_name or "mac" in os_name:
            plat = PlatformType.APPLE_SILICON
        elif "linux" in os_name:
            plat = PlatformType.LINUX_NVIDIA
        else:
            plat = PlatformType.CPU_ONLY

        # 2. Build CPU Profile
        cpu = CPUProfile(
            model=env.cpu_name,
            architecture=env.cpu_architecture,
            physical_cores=env.cpu_cores_physical,
            logical_cores=env.cpu_cores_logical,
            supports_avx2=True, # Assumption for modern systems
            tier=CPUTier.MEDIUM # Initial classification
        )

        # 3. Build RAM Profile
        ram = RAMProfile(
            total_gb=env.ram_gb,
            available_gb=env.ram_gb * 0.8, # Estimated
            usable_for_offload_gb=max(0, (env.ram_gb - 4.0) * 0.8),
            bandwidth_gbps=env.memory_bandwidth_gbps
        )

        # 4. Build Storage Profile
        storage = StorageProfile(
            path="root",
            total_gb=env.disk_total_gb or (env.disk_free_gb * 2),
            free_gb=env.disk_free_gb,
            storage_type=env.storage_type,
            estimated_read_mbps=env.storage_read_speed_mbps or 500,
            tier=StorageTier.FAST if "nvme" in env.storage_type.lower() else StorageTier.MODERATE
        )

        # 5. Build Form Factor
        ff = FormFactorProfile(
            is_laptop=(env.form_factor == "laptop"),
            sustained_performance_ratio=0.7 if env.form_factor == "laptop" else 1.0
        )

        # Compute capability conversion
        cc = None
        if env.cuda_compute_capability:
            try:
                cc = float(env.cuda_compute_capability)
            except (ValueError, TypeError):
                cc = None

        return HardwareProfile(
            platform=plat,
            gpu_vendor=env.gpu_vendor,
            gpu_name=env.gpu_name,
            vram_gb=env.vram_gb,
            cpu=cpu,
            ram=ram,
            storage=storage,
            form_factor=ff,
            compute_capability=cc,
            unified_memory=env.unified_memory
        )
