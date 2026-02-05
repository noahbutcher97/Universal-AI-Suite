"""
Centralized constants for the AI Universal Suite.
Reference for Task PAT-04: Model-to-Candidate Adapter and SYS-05.
"""

# --- Hardware & Resource Thresholds ---
OS_RESERVED_RAM_GB = 4.0      # Conservative RAM reserved for OS stability
OFFLOAD_SAFETY_FACTOR = 0.8   # % of available RAM usable for offload
STORAGE_SAFETY_BUFFER_GB = 10.0 # Safety buffer for OS stability (Task SYS-05)
VENV_SIZE_ESTIMATE_GB = 1.5   # Estimated disk size for a Python venv

# --- Recommendation Engine ---
DEFAULT_QUANT_PRIORITY = ["fp16", "bf16", "fp8", "q8_0", "q5_0", "q4_0"]
MPS_SAFE_QUANTS = {"q4_0", "q5_0", "q8_0", "f16", "f32", "fp16", "bf16"}

# --- Installation & Infrastructure ---
MAX_DOWNLOAD_RETRIES = 3
DOWNLOAD_CHUNK_SIZE = 1024 * 1024  # 1MB
DEFAULT_API_TIMEOUT = 30           # seconds
