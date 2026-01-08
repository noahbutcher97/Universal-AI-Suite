# AI Universal Suite - Technical Specification v3.0

**Status**: Consolidated specification incorporating all research findings
**Date**: January 2026
**Supersedes**: AI_UNIVERSAL_SUITE_SPECS.md v2.0, all SPEC_ADDENDUM documents

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Strategic Vision](#2-strategic-vision)
3. [Architecture Overview](#3-architecture-overview)
4. [Hardware Detection &amp; Platform Support](#4-hardware-detection--platform-support)
5. [Onboarding System](#5-onboarding-system)
6. [Three-Layer Recommendation Engine](#6-three-layer-recommendation-engine)
7. [Model Database Schema](#7-model-database-schema)
8. [Cloud API Integration](#8-cloud-api-integration)
9. [User Flow](#9-user-flow)
10. [Data Schemas](#10-data-schemas)
11. [Service Layer Specifications](#11-service-layer-specifications)
12. [UI Component Specifications](#12-ui-component-specifications)
13. [File Structure](#13-file-structure)
14. [Implementation Phases](#14-implementation-phases)
15. [Testing Requirements](#15-testing-requirements)

---

## 1. Executive Summary

AI Universal Suite is a cross-platform desktop application that transforms a user's computer into a fully configured AI workstation through a guided setup wizard. The application targets professionals who want to leverage AI tools without writing code, using terminals, or navigating complex installations.

### 1.1 Core Principles

1. **Zero Terminal Interaction**: Every action achievable through GUI
2. **Hardware-Aware Intelligence**: Automatic detection and optimization for user's specific hardware
3. **Use-Case Driven**: Start from "what you want to accomplish" not "what software to install"
4. **Platform Parity**: First-class support for Windows/NVIDIA (40%), Mac/Apple Silicon (40%), Linux/AMD (20%)
5. **Honest Constraints**: Clearly communicate what's possible vs impossible on user's hardware

### 1.2 Key Capabilities

- **100+ AI models** across image, video, audio, and 3D generation
- **Dual onboarding paths**: Quick Setup (5 questions, ~2 min) and Comprehensive Setup (15-20 questions, ~5-8 min)
- **Three-layer recommendation engine**: Constraint Satisfaction → Content-Based Filtering → TOPSIS ranking
- **Cloud API integration**: ComfyUI Partner Nodes for Veo3, Kling 2.0, Runway, etc.
- **Quantization support**: GGUF enables 14B parameter models on 8GB GPUs

### 1.3 Target User Platform Distribution

| Platform              | Share | Primary Optimization            |
| --------------------- | ----- | ------------------------------- |
| Windows + NVIDIA GPU  | 40%   | CUDA, FP8/FP16, Flash Attention |
| macOS + Apple Silicon | 40%   | MPS, GGUF quantization, MLX     |
| Linux + AMD ROCm      | 20%   | ROCm 6.4+, GGUF fallback        |

### 1.4 Related Documents

| Document | Location | Purpose |
|----------|----------|---------|
| Implementation Plan | `docs/plan/PLAN_v3.md` | Task tracker, decisions, issue tracking |
| Hardware Detection Spec | `docs/spec/HARDWARE_DETECTION.md` | Detailed hardware detection requirements |
| CUDA/PyTorch Installation | `docs/spec/CUDA_PYTORCH_INSTALLATION.md` | PyTorch auto-installation logic |
| Architecture Principles | `docs/ARCHITECTURE_PRINCIPLES.md` | Coding patterns and standards |
| Model Database | `data/models_database.yaml` | Model entries with variants |

---

## 2. Strategic Vision

### 2.1 Problem Statement

Experienced professionals (filmmakers, designers, developers, business owners) understand that AI tools could transform their work, but face barriers:

- Consumer AI apps lack control and consistency
- Professional tools require coding knowledge
- Subscription costs accumulate without clear ROI
- No unified system ties tools together
- Hardware requirements are confusing and poorly documented

### 2.2 Solution

AI Universal Suite provides:

1. **Intelligent Setup Wizard**: Dual-path onboarding (Quick or Comprehensive) with hardware-aware recommendations
2. **Use-Case Driven Configuration**: Start from outcomes, not software
3. **Honest Hardware Guidance**: Clear communication of capabilities and limitations per platform
4. **Unified Tool Management**: Manage ComfyUI, models, workflows, and API access from one interface
5. **Cloud/Local Hybrid**: Seamless fallback to cloud APIs when local hardware is insufficient

### 2.3 Target Users

| Persona               | Description                          | Primary Use Cases                         | Typical Hardware      |
| --------------------- | ------------------------------------ | ----------------------------------------- | --------------------- |
| Creative Professional | Filmmakers, designers, photographers | Image/video generation, content pipelines | Mac Studio, RTX 4090  |
| Knowledge Worker      | Business professionals, consultants  | AI assistants, document processing        | MacBook Pro, RTX 4060 |
| Technical Veteran     | Experienced developers learning AI   | Full stack integration, automation        | Linux workstation     |
| Solopreneur           | Independent business owners          | Productivity, content generation          | M2/M3 MacBook         |

---

## 3. Architecture Overview

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           UI Layer                                       │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────────────────────┐  │
│  │ Setup Wizard  │  │   Dashboard   │  │      Module Views           │  │
│  │  (Dual-Path)  │  │    (Main)     │  │  (ComfyUI/Models/Cloud)     │  │
│  └───────────────┘  └───────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Service Layer                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
│  │ Recommendation   │  │    Hardware      │  │   Cloud Offload      │   │
│  │    Engine        │  │    Detection     │  │     Strategy         │   │
│  │  (3-Layer)       │  │   (Platform)     │  │                      │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
│  │    Download      │  │     Model        │  │    Workflow          │   │
│  │    Service       │  │    Manager       │  │     Service          │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Configuration Layer                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
│  │  ConfigManager   │  │   models.yaml    │  │    OS Keyring        │   │
│  │   (config.json)  │  │ (Model Database) │  │   (API Keys)         │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        External Systems                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
│  │     ComfyUI      │  │  HuggingFace /   │  │   Partner Node       │   │
│  │   (Local Gen)    │  │    CivitAI       │  │   APIs (Cloud)       │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Module System

The application is organized around **modules** - discrete functional units that can be independently configured, installed, and launched.

| Module ID         | Display Name      | Description                                 | Status  |
| ----------------- | ----------------- | ------------------------------------------- | ------- |
| `comfyui`       | ComfyUI Studio    | Visual AI generation (image/video/audio/3D) | Core    |
| `cli_provider`  | AI Assistant CLI  | Command-line AI with file system access     | Core    |
| `model_manager` | Model Manager     | Download, organize, quantize models         | Core    |
| `cloud_apis`    | Cloud APIs        | Partner Node and third-party API management | Core    |
| `lm_studio`     | LM Studio         | Local LLM inference                         | Planned |
| `mcp_servers`   | MCP Configuration | Model Context Protocol servers              | Planned |

### 3.3 Recommendation Engine Architecture

The recommendation system uses a **three-layer architecture** validated by research on configuration wizards:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  INPUT: User Profile + Hardware Constraints + Selected Features         │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 1: CONSTRAINT SATISFACTION PROGRAMMING                           │
│  ─────────────────────────────────────────────                          │
│  • Binary elimination of impossible configurations                       │
│  • VRAM, RAM, storage, platform compatibility checks                    │
│  • Output: Viable candidates only + rejection reasons                   │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 2: CONTENT-BASED FEATURE MATCHING                                │
│  ─────────────────────────────────────────────                          │
│  • Cosine similarity between user needs and model capabilities          │
│  • No user history required (cold-start immune)                         │
│  • Output: Similarity-scored candidates                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LAYER 3: TOPSIS MULTI-CRITERIA RANKING                                 │
│  ─────────────────────────────────────────────                          │
│  • Weighted criteria (5): content_similarity, hardware_fit,             │
│    speed_fit, ecosystem_maturity, approach_fit                          │
│  • Output: Final ranked list with closeness coefficients                │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  OUTPUT: RankedCandidates with explainable scores and reasoning         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Hardware Detection & Platform Support

### 4.1 Detection Architecture

Hardware detection must be **platform-specific** rather than unified. Each platform has unique APIs, constraints, and optimization opportunities.

#### 4.1.1 Primary Detection Factors

| Factor                  | Impact                        | Detection Method                   |
| ----------------------- | ----------------------------- | ---------------------------------- |
| GPU Vendor              | Model compatibility           | Platform-specific APIs             |
| VRAM / Unified Memory   | Model size limits             | nvidia-smi, sysctl, rocminfo       |
| CUDA Compute Capability | Precision support (FP8, BF16) | torch.cuda.get_device_capability() |
| System RAM              | CPU offload capability        | OS APIs                            |
| Storage Type            | Model loading speed           | OS disk APIs                       |
| Memory Bandwidth        | LLM inference speed           | Lookup table by chip               |

#### 4.1.2 Secondary Detection Factors

| Factor             | Impact                        | Detection Method    |
| ------------------ | ----------------------------- | ------------------- |
| Thermal State      | Sustained workload capability | nvidia-smi, IOKit   |
| PCIe Configuration | Multi-GPU, CPU offload speed  | lspci, nvidia-smi   |
| CPU Single-Thread  | Workflow orchestration speed  | Benchmark lookup    |
| Power State        | Battery vs AC performance     | OS APIs             |
| Form Factor        | Thermal constraints           | Inferred from model |

### 4.2 Apple Silicon Detection

```python
class AppleSiliconDetector:
    """
    Detection strategy for Apple Silicon Macs.
    40% of target user base.
    """
  
    def detect(self) -> HardwareProfile:
        # Chip identification
        chip_string = subprocess.check_output(
            ["sysctl", "-n", "machdep.cpu.brand_string"]
        ).decode().strip()  # "Apple M1 Pro"
  
        # Unified memory (total system memory available to GPU)
        mem_bytes = int(subprocess.check_output(
            ["sysctl", "-n", "hw.memsize"]
        ).decode().strip())
        unified_memory_gb = mem_bytes / (1024**3)
  
        # Effective GPU memory (75% ceiling enforced by macOS)
        effective_vram_gb = unified_memory_gb * 0.75
  
        # MPS availability
        mps_available = torch.backends.mps.is_available()
  
        # Memory bandwidth (cannot detect directly - use lookup table)
        bandwidth_gbps = self.BANDWIDTH_LOOKUP.get(
            self._parse_chip_model(chip_string), 
            68  # Conservative M1 default
        )
  
        return HardwareProfile(
            platform="apple_silicon",
            gpu_vendor="apple",
            gpu_name=chip_string,
            vram_gb=effective_vram_gb,
            unified_memory=True,
            ram_gb=unified_memory_gb,
            memory_bandwidth_gbps=bandwidth_gbps,
            compute_capability=None,  # Not applicable
            mps_available=mps_available,
            supports_fp8=False,  # FP8 not supported on MPS
            supports_bf16=False,  # BF16 not hardware-accelerated
            flash_attention_available=False,
        )
  
    BANDWIDTH_LOOKUP = {
        "M1": 68,
        "M1 Pro": 200,
        "M1 Max": 400,
        "M1 Ultra": 800,
        "M2": 100,
        "M2 Pro": 200,
        "M2 Max": 400,
        "M2 Ultra": 800,
        "M3": 100,
        "M3 Pro": 150,
        "M3 Max": 400,
        "M4": 120,
        "M4 Pro": 273,
        "M4 Max": 546,
    }
```

#### Apple Silicon Critical Constraints

| Constraint                | Impact                          | Workaround                 |
| ------------------------- | ------------------------------- | -------------------------- |
| FP8 not supported         | Cannot use FP8 quantized models | Use GGUF or FP16           |
| 75% memory ceiling        | Reduces effective VRAM          | Account in calculations    |
| No Docker GPU passthrough | Must run natively               | Direct installation        |
| No Flash Attention        | Slower attention computation    | Accept slower speed        |
| BF16 not accelerated      | Use FP16 instead                | Auto-select FP16           |
| Non-K GGUF only           | K-quants crash on MPS           | Filter to Q4_0, Q5_0, Q8_0 |

#### Apple Silicon Video Generation Guidance

| Model        | Status          | Recommendation                   |
| ------------ | --------------- | -------------------------------- |
| AnimateDiff  | ✅ Full support | Primary video option             |
| Wan 2.x GGUF | ⚠️ Limited    | GGUF Q5/Q6 with Euler sampler    |
| HunyuanVideo | ❌ Impractical  | ~16 min per short clip on M3 Pro |
| LTX-Video    | ⚠️ Limited    | Experimental only                |

**Explicit recommendation**: Surface AnimateDiff as the primary video generation option for Apple Silicon users. Exclude HunyuanVideo from recommendations entirely.

### 4.3 Windows/NVIDIA Detection

```python
class NVIDIADetector:
    """
    Detection strategy for Windows/Linux with NVIDIA GPUs.
    40% of target user base (Windows) + portion of 20% Linux.
    """
  
    def detect(self) -> HardwareProfile:
        if not torch.cuda.is_available():
            raise NoCUDAError()
  
        # GPU identification
        gpu_name = torch.cuda.get_device_name(0)
        vram_bytes = torch.cuda.get_device_properties(0).total_memory
        vram_gb = vram_bytes / (1024**3)
  
        # Compute capability determines available optimizations
        major, minor = torch.cuda.get_device_capability(0)
        compute_capability = float(f"{major}.{minor}")
  
        # Multi-GPU detection
        gpu_count = torch.cuda.device_count()
  
        # NVLink topology (affects multi-GPU performance)
        nvlink_available = self._check_nvlink() if gpu_count > 1 else False
  
        # WSL2 detection
        is_wsl = self._detect_wsl()
  
        return HardwareProfile(
            platform="windows_nvidia" if not is_wsl else "wsl2_nvidia",
            gpu_vendor="nvidia",
            gpu_name=gpu_name,
            vram_gb=vram_gb,
            unified_memory=False,
            ram_gb=psutil.virtual_memory().total / (1024**3),
            compute_capability=compute_capability,
            supports_fp8=compute_capability >= 8.9,
            supports_bf16=compute_capability >= 8.0,
            supports_tf32=compute_capability >= 8.0,
            flash_attention_available=compute_capability >= 8.0,
            gpu_count=gpu_count,
            nvlink_available=nvlink_available,
        )
  
    def _detect_wsl(self) -> bool:
        try:
            with open("/proc/version", "r") as f:
                return "microsoft" in f.read().lower()
        except FileNotFoundError:
            return False
```

#### CUDA Compute Capability Feature Matrix

| CC   | Architecture | GPU Examples   | FP8 | BF16 | Flash Attn 2 | TF32 |
| ---- | ------------ | -------------- | --- | ---- | ------------ | ---- |
| 7.5  | Turing       | RTX 2080, T4   | ❌  | ❌   | ❌           | ❌   |
| 8.0  | Ampere       | A100           | ❌  | ✅   | ✅           | ✅   |
| 8.6  | Ampere       | RTX 3090, 3080 | ❌  | ✅   | ✅           | ✅   |
| 8.9  | Ada          | RTX 4090, 4080 | ✅  | ✅   | ✅           | ✅   |
| 9.0  | Hopper       | H100           | ✅  | ✅   | ✅ (v3)      | ✅   |
| 10.0 | Blackwell    | B200           | ✅  | ✅   | ✅           | ✅   |
| 12.0 | Blackwell    | RTX 5090       | ✅  | ✅   | ✅           | ✅   |

#### PyTorch Backend Configuration by Compute Capability

```python
def configure_pytorch_backends(compute_capability: float) -> dict:
    """Configure optimal PyTorch settings based on detected hardware."""
  
    config = {
        'torch.backends.cuda.matmul.allow_tf32': False,
        'torch.backends.cudnn.allow_tf32': False,
        'torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction': False,
        'torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction': False,
    }
    warnings = []
  
    if compute_capability >= 8.0:
        # Enable TF32 for Ampere+ (~10x speedup, negligible accuracy loss)
        config['torch.backends.cuda.matmul.allow_tf32'] = True
        config['torch.backends.cudnn.allow_tf32'] = True
        config['torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction'] = True
  
    if compute_capability >= 8.9:
        # FP16 reduced precision safe on Ada+
        config['torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction'] = True
  
    if compute_capability < 8.0:
        warnings.append("Flash Attention unavailable - using math backend (slower)")
  
    return config, warnings
```

### 4.4 Linux/AMD ROCm Detection

```python
class AMDROCmDetector:
    """
    Detection strategy for Linux with AMD GPUs.
    ~20% of target user base.
    """
  
    def detect(self) -> HardwareProfile:
        # ROCm version
        rocm_version = self._get_rocm_version()
  
        # GPU architecture
        gpu_info = subprocess.check_output(
            ["rocminfo"]
        ).decode()
        gfx_version = self._parse_gfx_version(gpu_info)  # e.g., "gfx1100"
  
        # VRAM
        vram_output = subprocess.check_output(
            ["amd-smi", "static", "--vram"]
        ).decode()
        vram_gb = self._parse_vram(vram_output)
  
        return HardwareProfile(
            platform="linux_rocm",
            gpu_vendor="amd",
            gpu_name=self._parse_gpu_name(gpu_info),
            vram_gb=vram_gb,
            unified_memory=False,
            ram_gb=psutil.virtual_memory().total / (1024**3),
            rocm_version=rocm_version,
            gfx_version=gfx_version,
            officially_supported=self._is_officially_supported(gfx_version),
        )
  
    OFFICIALLY_SUPPORTED_GFX = {
        "gfx1100": "RX 7900 XTX/XT",
        "gfx1101": "RX 7900 GRE",
        "gfx1102": "RX 7800 XT/7700 XT",
    }
  
    RDNA2_WORKAROUND = {
        "gfx1030": ("RX 6900 XT/6800", "HSA_OVERRIDE_GFX_VERSION=10.3.0"),
        "gfx1031": ("RX 6700 XT", "HSA_OVERRIDE_GFX_VERSION=10.3.0"),
    }
```

#### AMD ROCm Constraints

| Constraint                       | Impact                         | Mitigation                 |
| -------------------------------- | ------------------------------ | -------------------------- |
| RDNA2 requires workaround        | Stability risk                 | Warn user, provide env var |
| No TensorRT                      | Some optimizations unavailable | Use native PyTorch         |
| Flash Attention variants limited | Some FA not available          | Fall back to math backend  |
| CUDA-specific nodes fail         | Some ComfyUI nodes             | Filter incompatible nodes  |

### 4.5 Hardware Tier Classification

Based on detection, classify users into capability tiers:

| Tier                   | VRAM    | Recommended Models            | Video Capability      |
| ---------------------- | ------- | ----------------------------- | --------------------- |
| **Entry**        | 4-6GB   | SD1.5, SDXL Q4                | AnimateDiff only      |
| **Consumer**     | 8GB     | SDXL, Flux Q4-Q5, Wan TI2V 5B | Wan 5B, LTX 2B        |
| **Prosumer**     | 12GB    | Flux FP8, Wan 14B Q5          | Full Wan 2.2 Q5       |
| **Professional** | 16-24GB | All FP8, HunyuanVideo         | All local models      |
| **Workstation**  | 48GB+   | All FP16                      | Training, multi-model |

### 4.6 Secondary Hardware Factors

#### 4.6.1 Thermal Throttling Detection

```python
def check_thermal_state() -> ThermalState:
    """
    Check if GPU is thermally constrained.
    AI workloads generate sustained 100% load - different from gaming bursts.
    """
    if platform == "nvidia":
        output = subprocess.check_output(
            ["nvidia-smi", "-q", "-d", "TEMPERATURE"]
        ).decode()
        temp = parse_gpu_temp(output)
  
        if temp >= 85:
            return ThermalState.CRITICAL  # Active throttling
        elif temp >= 82:
            return ThermalState.WARNING   # Approaching throttle
        else:
            return ThermalState.NORMAL
```

**Thermal-based recommendations:**

- At WARNING: Suggest enabling tiled VAE, reducing batch size
- At CRITICAL: Surface cooling upgrade recommendation
- Apple Silicon: Generally efficient, no adjustment needed

#### 4.6.2 Storage Speed Detection

| Storage Type | Sequential Read | 10GB Model Load | Impact                    |
| ------------ | --------------- | --------------- | ------------------------- |
| NVMe Gen 4   | 7,000 MB/s      | 1.4 seconds     | Optimal                   |
| NVMe Gen 3   | 3,500 MB/s      | 2.9 seconds     | Good                      |
| SATA SSD     | 600 MB/s        | 16.7 seconds    | Acceptable                |
| HDD          | 120-160 MB/s    | 83 seconds      | **Not recommended** |

```python
def detect_storage_type(path: str) -> StorageType:
    """Detect storage interface type for model directory."""
    if sys.platform == "win32":
        # Use WMI or DeviceIoControl
        pass
    elif sys.platform == "darwin":
        # Use diskutil info
        pass
    else:
        # Use /sys/block/
        pass
```

**Storage-based recommendations:**

- HDD detected: Display prominent warning "AI model loading will be extremely slow"
- <32GB RAM + SATA SSD: Recommend NVMe upgrade for model swapping
- Factor storage speed into "estimated workflow time" calculations

#### 4.6.3 Memory Bandwidth Impact

Memory bandwidth determines LLM/text encoder inference speed (memory-bound, not compute-bound):

| Memory Type   | Bandwidth   | Workload Impact             |
| ------------- | ----------- | --------------------------- |
| GDDR6         | 768 GB/s    | Adequate for <13B models    |
| GDDR6X        | ~1 TB/s     | Good for 13B-70B            |
| HBM2e         | 1.6 TB/s    | Required for 70B+ training  |
| Apple Unified | 68-800 GB/s | Varies by chip (see lookup) |

**Bandwidth-based recommendations:**

- GDDR6 system: Prefer smaller text encoders (CLIP over T5-XXL)
- High bandwidth: Can recommend T5-XXL with Flux without penalty

---

## 5. Onboarding System

### 5.1 Dual-Path Architecture

The onboarding system offers two paths to accommodate different user types:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  How would you like to set up your AI workstation?                      │
│                                                                         │
│  ┌─────────────────────────┐    ┌─────────────────────────────────┐    │
│  │  🚀 Quick Setup         │    │  🎯 Comprehensive Setup         │    │
│  │  (~2 minutes)           │    │  (~5-8 minutes)                 │    │
│  │                         │    │                                 │    │
│  │  5 questions            │    │  15-20 questions                │    │
│  │  Smart defaults         │    │  Precise recommendations        │    │
│  │  Easy to adjust later   │    │  Optimized for your needs       │    │
│  │                         │    │                                 │    │
│  │  Best for exploring     │    │  Best if you know what          │    │
│  │  or getting started     │    │  you want to create             │    │
│  └─────────────────────────┘    └─────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Quick Setup Path (5 Questions)

For users who want to explore or get started quickly with smart defaults.

#### Question 1: Primary Use Case

```yaml
question: "What do you want to create?"
type: multi_select
options:
  - id: images
    label: "Images"
    description: "Generate and edit photos, art, and graphics"
    icon: 🎨
  - id: video
    label: "Video"
    description: "Animate images and generate video clips"
    icon: 🎬
  - id: audio
    label: "Audio"
    description: "Voice synthesis, music, and sound effects"
    icon: 🎵
  - id: 3d
    label: "3D Models"
    description: "Generate 3D objects and textures"
    icon: 🎲
  - id: everything
    label: "Everything"
    description: "Full AI workstation with all capabilities"
    icon: 🚀
min_selections: 1
```

#### Question 2: Experience Level

```yaml
question: "How familiar are you with AI generation tools?"
type: single_select
options:
  - id: new_to_ai
    label: "New to AI"
    description: "I haven't used AI image/video tools before"
  - id: tried_few
    label: "Tried a few"
    description: "I've used Midjourney, DALL-E, or similar"
  - id: regular
    label: "Regular user"
    description: "I use AI tools regularly and understand basics"
  - id: power_user
    label: "Power user"
    description: "I've used ComfyUI, Automatic1111, or similar"
```

#### Question 3: Priority Slider

```yaml
question: "What matters more to you?"
type: slider
left_label: "Speed & Simplicity"
left_description: "Faster results, simpler setup"
right_label: "Quality & Control"
right_description: "Best output, more options"
default: 0.5
```

#### Question 4: Cloud Willingness (Conditional)

```yaml
question: "Are you open to using cloud APIs for demanding tasks?"
type: single_select
show_if: "hardware.vram_gb < 16 OR use_case includes 'video'"
options:
  - id: local_only
    label: "Local only"
    description: "I'll use quantized versions or skip incompatible models"
  - id: cloud_fallback
    label: "Cloud as fallback"
    description: "Suggest cloud when local isn't possible"
  - id: cloud_preferred
    label: "Cloud preferred for heavy tasks"
    description: "Route demanding models to cloud automatically"
default: cloud_fallback
```

#### Question 5: API Key (Optional)

```yaml
question: "Do you have an API key for AI services?"
type: api_key_input
providers:
  - anthropic
  - openai
  - google
skip_allowed: true
skip_label: "I'll add this later"
```

### 5.3 Comprehensive Setup Path (Tiered Progressive)

For users who know what they want and prefer precise recommendations.

#### Tier 1: Foundation (Required - 4 Questions)

```yaml
tier: 1
title: "Foundation"
description: "Core preferences that shape all recommendations"
questions:
  - id: use_cases
    question: "What do you want to create?"
    type: multi_select
    options: [images, video, audio, 3d]
  
  - id: experience_level
    question: "How familiar are you with AI generation tools?"
    type: single_select
    options: [new_to_ai, tried_few, regular, power_user]
  
  - id: priority_slider
    question: "What matters more to you?"
    type: slider
    range: [speed_simplicity, quality_control]
  
  - id: cloud_willingness
    question: "How do you want to handle demanding models?"
    type: single_select
    options: [local_only, cloud_fallback, cloud_preferred]
```

#### Tier 2: Image Generation (Conditional - 3-5 Questions)

```yaml
tier: 2
title: "Image Generation"
show_if: "use_cases includes 'images'"
questions:
  - id: image_style
    question: "What style of images do you create most?"
    type: multi_select
    options:
      - id: photorealistic
        label: "Photorealistic"
        description: "Photos, portraits, products"
      - id: cinematic
        label: "Cinematic"
        description: "Movie stills, dramatic lighting"
      - id: illustration
        label: "Illustration"
        description: "Digital art, concept art"
      - id: anime
        label: "Anime/Manga"
        description: "Japanese animation style"
      - id: artistic
        label: "Artistic/Abstract"
        description: "Fine art, experimental"
  
  - id: editing_needs
    question: "What editing capabilities do you need?"
    type: multi_select
    options:
      - id: inpainting
        label: "Inpainting"
        description: "Edit specific areas of images"
      - id: instruction_editing
        label: "Instruction editing"
        description: "Edit via text commands like 'make her smile'"
      - id: background_replacement
        label: "Background replacement"
        description: "Change or remove backgrounds"
      - id: object_removal
        label: "Object removal"
        description: "Remove unwanted elements"
      - id: style_transfer
        label: "Style transfer"
        description: "Apply artistic styles to photos"
  
  - id: text_rendering
    question: "How important is accurate text in images?"
    type: single_select
    options:
      - id: not_needed
        label: "Not needed"
      - id: occasional
        label: "Occasional use"
        description: "Sometimes need readable text"
      - id: critical
        label: "Critical"
        description: "Posters, signage, text-heavy work"
  
  - id: character_consistency
    question: "Do you need the same character across multiple images?"
    type: single_select
    options:
      - id: not_needed
        label: "Not needed"
      - id: helpful
        label: "Would be helpful"
      - id: essential
        label: "Essential"
        description: "Comics, storyboards, character design"
  
  # Advanced expander
  - id: advanced_image
    type: expander
    label: "Advanced options"
    questions:
      - id: controlnet_types
        question: "Which structural controls do you need?"
        type: multi_select
        options: [pose, depth, canny_edge, segmentation, lineart]
      - id: specific_models
        question: "Any specific models you want?"
        type: text_input
        placeholder: "e.g., Juggernaut XL, RealVis"
```

#### Tier 3: Video Generation (Conditional - 4-6 Questions)

```yaml
tier: 3
title: "Video Generation"
show_if: "use_cases includes 'video'"
questions:
  - id: video_modes
    question: "How do you want to create videos?"
    type: multi_select
    options:
      - id: t2v
        label: "Text to Video"
        description: "Generate video from text descriptions"
      - id: i2v
        label: "Image to Video"
        description: "Animate still images"
      - id: flf2v
        label: "First-Last Frame"
        description: "Interpolate between keyframes"
      - id: video_editing
        label: "Video Editing"
        description: "Modify existing videos"
  
  - id: video_duration
    question: "How long do your videos need to be?"
    type: single_select
    options:
      - id: short
        label: "Short clips (2-5 seconds)"
      - id: medium
        label: "Medium clips (5-10 seconds)"
      - id: long
        label: "Longer videos (10+ seconds)"
        description: "May require cloud APIs or high-end hardware"
  
  - id: audio_sync
    question: "Do you need audio synchronized with video?"
    type: multi_select
    options:
      - id: none
        label: "No audio needed"
      - id: lip_sync
        label: "Lip sync"
        description: "Match mouth movements to speech"
      - id: ambient
        label: "Ambient audio"
        description: "Background sounds, atmosphere"
      - id: music
        label: "Music sync"
        description: "Video timed to music"
  
  - id: camera_control
    question: "Do you need camera movement control?"
    type: single_select
    options:
      - id: not_needed
        label: "Not needed"
      - id: basic
        label: "Basic"
        description: "Pan, zoom, tilt"
      - id: advanced
        label: "Advanced"
        description: "Complex camera paths, 3D movement"
  
  # Advanced expander
  - id: advanced_video
    type: expander
    label: "Advanced options"
    questions:
      - id: motion_intensity
        question: "Preferred motion intensity?"
        type: slider
        range: [subtle, dynamic]
      - id: frame_interpolation
        question: "Need frame interpolation for smoother video?"
        type: boolean
```

#### Tier 4: Audio Generation (Conditional - 2-4 Questions)

```yaml
tier: 4
title: "Audio Generation"
show_if: "use_cases includes 'audio'"
questions:
  - id: audio_types
    question: "What types of audio do you need?"
    type: multi_select
    options:
      - id: tts
        label: "Text to Speech"
        description: "Convert text to spoken audio"
      - id: voice_clone
        label: "Voice Cloning"
        description: "Clone voices from samples"
      - id: music
        label: "Music Generation"
        description: "Create music and songs"
      - id: sfx
        label: "Sound Effects"
        description: "Generate ambient sounds, effects"
  
  - id: voice_languages
    question: "What languages do you need for voice?"
    type: multi_select
    show_if: "audio_types includes 'tts' OR audio_types includes 'voice_clone'"
    options: [english, chinese, japanese, korean, spanish, french, german, other]
  
  - id: voice_quality
    question: "Voice quality priority?"
    type: single_select
    show_if: "audio_types includes 'tts' OR audio_types includes 'voice_clone'"
    options:
      - id: fast
        label: "Fast generation"
        description: "Good quality, quick results"
      - id: high_quality
        label: "High quality"
        description: "Best quality, slower generation"
```

#### Tier 5: 3D Generation (Conditional - 2-3 Questions)

```yaml
tier: 5
title: "3D Generation"
show_if: "use_cases includes '3d'"
questions:
  - id: 3d_output
    question: "What 3D output do you need?"
    type: multi_select
    options:
      - id: mesh
        label: "3D Meshes"
        description: "Polygonal models for games/rendering"
      - id: textured
        label: "Textured Models"
        description: "Models with materials/textures"
      - id: pbr
        label: "PBR Materials"
        description: "Physically-based rendering materials"
  
  - id: 3d_quality_speed
    question: "3D generation priority?"
    type: slider
    left_label: "Speed"
    right_label: "Quality"
```

#### Tier 6: Workflow Preferences (Always - 2 Questions)

```yaml
tier: 6
title: "Workflow Preferences"
always_show: true
questions:
  - id: complexity_tolerance
    question: "How much complexity are you comfortable with?"
    type: single_select
    options:
      - id: simple
        label: "Keep it simple"
        description: "Preset workflows, minimal configuration"
      - id: moderate
        label: "Some customization"
        description: "Adjust settings, try different models"
      - id: full_control
        label: "Full control"
        description: "Build custom workflows, access all options"
  
  - id: budget_sensitivity
    question: "For cloud API usage, what's your budget sensitivity?"
    type: single_select
    show_if: "cloud_willingness != 'local_only'"
    options:
      - id: cost_conscious
        label: "Cost conscious"
        description: "Show costs, prefer local when possible"
      - id: balanced
        label: "Balanced"
        description: "Use cloud when it makes sense"
      - id: quality_first
        label: "Quality first"
        description: "Best results regardless of cost"
```

### 5.4 Hardware Confirmation Screen

Shown after path selection, before questions:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  We detected your hardware                                              │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  💻 System: MacBook Pro 16" (2023)                              │   │
│  │  🎮 GPU: Apple M3 Max                                           │   │
│  │  🧠 Memory: 48GB Unified                                        │   │
│  │  💾 Storage: 1TB NVMe (523GB free)                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ✅ Great for: Image generation, basic video, audio             │   │
│  │  ⚠️ Limited: Advanced video (Wan 2.2 14B, HunyuanVideo)         │   │
│  │  💡 Tip: GGUF quantized models recommended for best performance │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  [This looks right]                    [Edit hardware info]            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.5 Progressive Disclosure Summary

| Path                           | Questions | Time   | Best For                   |
| ------------------------------ | --------- | ------ | -------------------------- |
| Quick Setup                    | 5         | ~2 min | Exploring, getting started |
| Comprehensive (images only)    | ~8        | ~3 min | Focused image work         |
| Comprehensive (video only)     | ~8        | ~3 min | Focused video work         |
| Comprehensive (full stack)     | ~18       | ~6 min | Professional setup         |
| Comprehensive (all + advanced) | ~25       | ~8 min | Power users                |

---

## 6. Three-Layer Recommendation Engine

### 6.1 Architecture Overview

The recommendation engine implements a **research-validated three-layer architecture** that separates concerns:

1. **Layer 1 (CSP)**: Binary elimination of impossible configurations
2. **Layer 2 (Content-Based)**: Feature similarity scoring
3. **Layer 3 (TOPSIS)**: Multi-criteria final ranking

This architecture is **cold-start immune** (no user history required) and provides **explainable recommendations** at each layer.

### 6.2 Layer 1: Constraint Satisfaction Programming

```python
class ConstraintSatisfactionLayer:
    """
    Layer 1: Binary elimination of candidates that violate hard constraints.
    Runs BEFORE any scoring to reduce candidate pool.
    """
  
    def filter_candidates(
        self, 
        candidates: List[ModelCandidate],
        hardware: HardwareProfile,
        user_constraints: UserConstraints
    ) -> Tuple[List[ModelCandidate], List[RejectionReason]]:
        """
        Returns (viable_candidates, rejections_with_reasons)
        """
        viable = []
        rejections = []
  
        for candidate in candidates:
            rejection = self._check_all_constraints(candidate, hardware, user_constraints)
            if rejection:
                rejections.append(rejection)
            else:
                viable.append(candidate)
  
        return viable, rejections
  
    def _check_all_constraints(
        self, 
        candidate: ModelCandidate,
        hardware: HardwareProfile,
        user_constraints: UserConstraints
    ) -> Optional[RejectionReason]:
        """Check all hard constraints. Any failure = immediate rejection."""
  
        # 1. VRAM constraint (with quantization fallback consideration)
        rejection = self._check_vram_constraint(candidate, hardware)
        if rejection:
            # NEW: Check if CPU offload can save this candidate
            if self._can_offload_to_cpu(candidate, hardware):
                candidate.execution_mode = "gpu_offload"
            else:
                return rejection
  
        # 2. RAM constraint
        rejection = self._check_ram_constraint(candidate, hardware)
        if rejection:
            return rejection
  
        # 3. Storage space constraint
        rejection = self._check_storage_constraint(candidate, hardware)
        if rejection:
            return rejection
  
        # 4. Platform compatibility
        rejection = self._check_platform_constraint(candidate, hardware)
        if rejection:
            return rejection
  
        # 5. Compute capability (for precision requirements)
        rejection = self._check_compute_capability(candidate, hardware)
        if rejection:
            return rejection
  
        # 6. User constraints (local-only, etc.)
        rejection = self._check_user_constraints(candidate, user_constraints)
        if rejection:
            return rejection
  
        return None  # Passes all constraints
  
    def _can_offload_to_cpu(
        self,
        candidate: ModelCandidate,
        hardware: HardwareProfile
    ) -> bool:
        """
        NEW: Check if model can run via CPU offload when VRAM insufficient.
        Requires: model supports offload + adequate CPU + sufficient RAM + AVX2.
        See: docs/spec/HARDWARE_DETECTION.md Section 3, 5
        """
        if not candidate.supports_cpu_offload:
            return False
        
        # CPU must be HIGH or MEDIUM tier for viable offload
        if hardware.cpu.tier not in (CPUTier.HIGH, CPUTier.MEDIUM):
            return False
        
        # GGUF models require AVX2 for reasonable performance
        is_gguf = any('gguf' in v.precision.lower() for v in candidate.variants)
        if is_gguf and not hardware.cpu.supports_avx2:
            return False
        
        # Must have enough RAM for offloaded layers
        ram_needed = candidate.ram_for_offload_gb or candidate.min_vram_gb
        if hardware.ram.usable_for_offload_gb < ram_needed:
            return False
        
        return True
  
    def _check_vram_constraint(
        self, 
        candidate: ModelCandidate,
        hardware: HardwareProfile
    ) -> Optional[RejectionReason]:
        """
        VRAM check with quantization fallback logic.
        """
        effective_vram = (
            hardware.ram_gb * 0.75 
            if hardware.unified_memory 
            else hardware.vram_gb
        )
  
        # Check if any variant fits
        for variant in candidate.variants:
            if variant.vram_min_mb / 1024 <= effective_vram:
                # At least one variant fits
                return None
  
        # No variant fits - check if cloud fallback available
        if candidate.cloud_available:
            # Don't reject, mark for cloud suggestion
            candidate.requires_cloud = True
            return None
  
        return RejectionReason(
            candidate_id=candidate.id,
            constraint="vram",
            required_gb=candidate.min_vram_gb,
            available_gb=effective_vram,
            message=f"Requires {candidate.min_vram_gb}GB VRAM, only {effective_vram:.1f}GB available. No quantized or cloud version available."
        )
  
    def _check_platform_constraint(
        self, 
        candidate: ModelCandidate,
        hardware: HardwareProfile
    ) -> Optional[RejectionReason]:
        """
        Platform-specific compatibility check.
        Critical for Apple Silicon where many models are incompatible.
        """
        platform = hardware.platform
  
        # Check model's platform support
        if platform == "apple_silicon":
            if not candidate.supports_mps:
                return RejectionReason(
                    candidate_id=candidate.id,
                    constraint="platform",
                    message=f"{candidate.name} is not compatible with Apple Silicon"
                )
      
            # Check for FP8-only models
            if candidate.requires_fp8 and not hardware.supports_fp8:
                # Check if GGUF alternative exists
                if not any(v.precision.startswith("gguf") for v in candidate.variants):
                    return RejectionReason(
                        candidate_id=candidate.id,
                        constraint="precision",
                        message=f"{candidate.name} requires FP8 which is not supported on Apple Silicon"
                    )
  
        elif platform == "linux_rocm":
            if candidate.cuda_only:
                return RejectionReason(
                    candidate_id=candidate.id,
                    constraint="platform",
                    message=f"{candidate.name} requires CUDA and is not compatible with ROCm"
                )
  
        return None

    def _check_storage_constraint(
        self,
        candidate: ModelCandidate,
        hardware: HardwareProfile
    ) -> Optional[RejectionReason]:
        """
        NEW: Check if storage has enough free space for model.
        See: docs/spec/HARDWARE_DETECTION.md Section 4
        """
        model_size_gb = candidate.total_size_gb
        buffer_gb = 10  # Reserve for workspace, temp files
        
        if not hardware.storage.can_fit(model_size_gb, buffer_gb):
            return RejectionReason(
                candidate_id=candidate.id,
                constraint="storage_space",
                required_gb=model_size_gb,
                available_gb=hardware.storage.free_gb,
                message=f"Requires {model_size_gb:.1f}GB storage, only {hardware.storage.free_gb:.1f}GB available"
            )
        
        return None
```

### 6.3 Layer 2: Content-Based Feature Matching

Layer 2 scores candidates based on feature similarity to user needs using cosine similarity. It is cold-start immune (no user history required).

#### 6.3.1 Modular Modality Architecture

Use cases often span multiple modalities (e.g., character animation needs image + video). The Layer 2 architecture separates concerns by modality:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      MODALITY PREFERENCE SCHEMAS                        │
├─────────────────────────────────────────────────────────────────────────┤
│  SharedQualityPrefs          │  Cross-cutting quality preferences       │
│    - photorealism            │  (applies to all modalities)             │
│    - artistic_stylization    │                                          │
│    - generation_speed        │                                          │
│    - output_quality          │                                          │
│    - character_consistency   │                                          │
├──────────────────────────────┼──────────────────────────────────────────┤
│  ImageModalityPrefs          │  Image-specific preferences              │
│    - editability             │                                          │
│    - pose_control            │                                          │
│    - holistic_edits          │                                          │
│    - localized_edits         │                                          │
│    - style_tags              │                                          │
├──────────────────────────────┼──────────────────────────────────────────┤
│  VideoModalityPrefs          │  Video-specific preferences              │
│    - motion_intensity        │  (1=subtle, 5=dynamic)                   │
│    - temporal_coherence      │                                          │
│    - duration_preference     │                                          │
├──────────────────────────────┼──────────────────────────────────────────┤
│  AudioModalityPrefs          │  Audio-specific (future)                 │
│  ThreeDModalityPrefs         │  3D-specific (future)                    │
└──────────────────────────────┴──────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       USE CASE COMPOSITION                              │
├─────────────────────────────────────────────────────────────────────────┤
│  UseCaseDefinition                                                      │
│    - id: "character_animation"                                          │
│    - name: "Character Animation Workflow"                               │
│    - required_modalities: ["image", "video"]                            │
│    - shared: SharedQualityPrefs(...)                                    │
│    - image: ImageModalityPrefs(...) | None                              │
│    - video: VideoModalityPrefs(...) | None                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      MODALITY SCORERS                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  ContentBasedLayer                                                      │
│    scorers: Dict[str, ModalityScorer] = {                               │
│      "image": ImageScorer(),                                            │
│      "video": VideoScorer(),                                            │
│      "audio": AudioScorer(),  # future                                  │
│    }                                                                    │
│                                                                         │
│    def score_for_use_case(candidates, use_case: UseCaseDefinition):     │
│      results = {}                                                       │
│      for modality in use_case.required_modalities:                      │
│        scorer = self.scorers[modality]                                  │
│        modality_prefs = getattr(use_case, modality)                     │
│        results[modality] = scorer.score(candidates, modality_prefs,     │
│                                         use_case.shared)                │
│      return results                                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

**Design Benefits**:
- **Single Responsibility**: Each scorer only handles its modality's dimensions
- **Open/Closed**: Add new modalities without modifying existing scorers
- **Composable**: Use cases declare their modality requirements
- **Testable**: Each modality scorer can be tested in isolation

#### 6.3.2 Modality Scorer Interface

```python
from abc import ABC, abstractmethod

class ModalityScorer(ABC):
    """Base class for modality-specific scoring."""

    # Dimensions this scorer evaluates
    DIMENSIONS: List[str] = []

    # Weights for each dimension
    DIMENSION_WEIGHTS: Dict[str, float] = {}

    @abstractmethod
    def build_user_vector(
        self,
        modality_prefs: Any,
        shared_prefs: SharedQualityPrefs
    ) -> Dict[str, float]:
        """Build user preference vector for this modality."""
        pass

    @abstractmethod
    def build_model_vector(self, model: ModelEntry) -> Dict[str, float]:
        """Build model capability vector for this modality."""
        pass

    def score(
        self,
        candidates: List[PassingCandidate],
        modality_prefs: Any,
        shared_prefs: SharedQualityPrefs
    ) -> List[ScoredCandidate]:
        """Score candidates for this modality."""
        user_vector = self.build_user_vector(modality_prefs, shared_prefs)
        scored = []
        for candidate in candidates:
            model_vector = self.build_model_vector(candidate.model)
            similarity = self._cosine_similarity(user_vector, model_vector)
            scored.append(ScoredCandidate(
                passing_candidate=candidate,
                similarity_score=similarity,
                modality=self.__class__.__name__.replace("Scorer", "").lower()
            ))
        return scored
```

#### 6.3.3 Original Implementation (Flat Vector)

The following shows the original flat-vector approach for reference. New implementations should use the modular architecture above.

```python
class ContentBasedLayer:
    """
    Layer 2: Score candidates based on feature similarity to user needs.
    Uses content attributes, not collaborative signals.
    Cold-start immune - no user history required.
    """
  
    def score_candidates(
        self,
        candidates: List[ModelCandidate],
        user_profile: UserProfile
    ) -> List[ScoredCandidate]:
        """
        Score each candidate by cosine similarity to user needs.
        Returns candidates with content_similarity_score (0-1).
        """
        user_vector = self._build_user_feature_vector(user_profile)
        scored = []
  
        for candidate in candidates:
            model_vector = self._build_model_feature_vector(candidate)
            similarity = self._cosine_similarity(user_vector, model_vector)
      
            # Feature match details for explanation
            matching_features = self._identify_matching_features(
                user_profile, candidate
            )
      
            scored.append(ScoredCandidate(
                candidate=candidate,
                content_similarity=similarity,
                matching_features=matching_features,
                missing_features=self._identify_missing_features(
                    user_profile, candidate
                )
            ))
  
        return scored
  
    def _build_user_feature_vector(self, profile: UserProfile) -> np.ndarray:
        """
        Convert user profile to normalized feature vector.
        Maps 5 aggregated factors to internal dimensions.
        """
        # Start with explicit factor scores
        vector = {
            # Quality factors
            'photorealism': profile.factors.quality_priority if profile.style_preferences.photorealistic else 0,
            'artistic_quality': profile.factors.quality_priority if profile.style_preferences.artistic else 0,
            'text_rendering': 1.0 if profile.text_rendering_importance == 'critical' else 0.5 if profile.text_rendering_importance == 'occasional' else 0,
      
            # Speed factors
            'generation_speed': profile.factors.speed_priority,
            'iteration_speed': profile.factors.speed_priority * 0.8,
      
            # Control factors
            'pose_control': 1.0 if 'pose' in profile.controlnet_needs else 0,
            'depth_control': 1.0 if 'depth' in profile.controlnet_needs else 0,
            'composition_control': profile.factors.control_priority,
      
            # Consistency factors
            'character_consistency': 1.0 if profile.character_consistency == 'essential' else 0.5 if profile.character_consistency == 'helpful' else 0,
      
            # Capability factors
            'inpainting': 1.0 if 'inpainting' in profile.editing_needs else 0,
            'instruction_editing': 1.0 if 'instruction_editing' in profile.editing_needs else 0,
            't2v': 1.0 if 't2v' in profile.video_modes else 0,
            'i2v': 1.0 if 'i2v' in profile.video_modes else 0,
            'flf2v': 1.0 if 'flf2v' in profile.video_modes else 0,
            'lip_sync': 1.0 if 'lip_sync' in profile.audio_sync_needs else 0,
            'voice_clone': 1.0 if 'voice_clone' in profile.audio_types else 0,
        }
  
        return self._normalize_vector(list(vector.values()))
  
    def _build_model_feature_vector(self, candidate: ModelCandidate) -> np.ndarray:
        """
        Convert model capabilities to normalized feature vector.
        Same dimensions as user vector for cosine similarity.
        """
        caps = candidate.capabilities
        vector = {
            'photorealism': caps.photorealism_score,
            'artistic_quality': caps.artistic_score,
            'text_rendering': caps.text_rendering_score,
            'generation_speed': caps.speed_score,
            'iteration_speed': caps.iteration_score,
            'pose_control': 1.0 if 'pose' in caps.controlnet_support else 0,
            'depth_control': 1.0 if 'depth' in caps.controlnet_support else 0,
            'composition_control': caps.composition_control_score,
            'character_consistency': caps.consistency_score,
            'inpainting': caps.inpainting_score,
            'instruction_editing': caps.instruction_editing_score,
            't2v': 1.0 if 't2v' in caps.video_modes else 0,
            'i2v': 1.0 if 'i2v' in caps.video_modes else 0,
            'flf2v': 1.0 if 'flf2v' in caps.video_modes else 0,
            'lip_sync': 1.0 if caps.lip_sync_support else 0,
            'voice_clone': 1.0 if caps.voice_clone_support else 0,
        }
  
        return self._normalize_vector(list(vector.values()))
  
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        dot_product = np.dot(a, b)
        magnitude_a = np.linalg.norm(a)
        magnitude_b = np.linalg.norm(b)
  
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
  
        return dot_product / (magnitude_a * magnitude_b)
```

### 6.4 Layer 3: TOPSIS Multi-Criteria Ranking

```python
class TOPSISLayer:
    """
    Layer 3: TOPSIS (Technique for Order Preference by Similarity to Ideal Solution)
    Provides final ranking with interpretable "closeness to ideal" scores.
    
    Updated to include speed_fit criterion based on storage and form factor.
    See: docs/spec/HARDWARE_DETECTION.md
    """
  
    DEFAULT_WEIGHTS = {
        'content_similarity': 0.35,   # Reduced from 0.40
        'hardware_fit': 0.25,         # Reduced from 0.30
        'speed_fit': 0.15,            # NEW: Storage speed + form factor
        'ecosystem_maturity': 0.15,
        'approach_fit': 0.10,         # Reduced from 0.15
    }
    
    # Alternative weights when user prioritizes speed
    SPEED_PRIORITY_WEIGHTS = {
        'content_similarity': 0.25,
        'hardware_fit': 0.20,
        'speed_fit': 0.30,            # Elevated for speed-focused users
        'ecosystem_maturity': 0.15,
        'approach_fit': 0.10,
    }
  
    def rank_candidates(
        self,
        scored_candidates: List[ScoredCandidate],
        hardware: HardwareProfile,
        preference_weights: Optional[Dict[str, float]] = None
    ) -> List[RankedCandidate]:
        """
        Apply TOPSIS to produce final ranking.
        Returns candidates with closeness coefficients (0-1, higher = better).
        """
        if not scored_candidates:
            return []
  
        weights = preference_weights or self.DEFAULT_WEIGHTS
  
        # Step 1: Build decision matrix
        criteria = list(weights.keys())
        matrix = self._build_decision_matrix(
            scored_candidates, criteria, hardware
        )
  
        # Step 2: Normalize matrix (vector normalization)
        normalized = self._vector_normalize(matrix)
  
        # Step 3: Apply weights
        weight_vector = np.array([weights[c] for c in criteria])
        weighted = normalized * weight_vector
  
        # Step 4: Determine ideal and anti-ideal solutions
        ideal = weighted.max(axis=0)      # Best value per criterion
        anti_ideal = weighted.min(axis=0)  # Worst value per criterion
  
        # Step 5: Calculate distances
        dist_to_ideal = np.sqrt(((weighted - ideal) ** 2).sum(axis=1))
        dist_to_anti = np.sqrt(((weighted - anti_ideal) ** 2).sum(axis=1))
  
        # Step 6: Calculate closeness coefficient
        closeness = dist_to_anti / (dist_to_ideal + dist_to_anti + 1e-10)
  
        # Build ranked results with explanations
        ranked = []
        for i, scored in enumerate(scored_candidates):
            ranked.append(RankedCandidate(
                candidate=scored.candidate,
                topsis_score=float(closeness[i]),
                content_similarity=scored.content_similarity,
                matching_features=scored.matching_features,
                criteria_scores={
                    criteria[j]: float(weighted[i, j])
                    for j in range(len(criteria))
                },
                rank=0  # Set after sorting
            ))
  
        # Sort by TOPSIS score descending
        ranked.sort(key=lambda x: x.topsis_score, reverse=True)
        for i, r in enumerate(ranked):
            r.rank = i + 1
  
        return ranked
  
    def _build_decision_matrix(
        self,
        candidates: List[ScoredCandidate],
        criteria: List[str],
        hardware: HardwareProfile,
        user_preferences: UserPreferences  # NEW parameter
    ) -> np.ndarray:
        """Build decision matrix: rows=candidates, columns=criteria."""
        n_candidates = len(candidates)
        n_criteria = len(criteria)
        matrix = np.zeros((n_candidates, n_criteria))
  
        for i, scored in enumerate(candidates):
            for j, criterion in enumerate(criteria):
                if criterion == 'content_similarity':
                    matrix[i, j] = scored.content_similarity
                elif criterion == 'hardware_fit':
                    matrix[i, j] = self._compute_hardware_fit(
                        scored.candidate, hardware
                    )
                elif criterion == 'speed_fit':  # NEW
                    matrix[i, j] = self._compute_speed_fit(
                        scored.candidate, hardware, user_preferences
                    )
                elif criterion == 'ecosystem_maturity':
                    matrix[i, j] = scored.candidate.ecosystem_maturity_score
                elif criterion == 'approach_fit':
                    matrix[i, j] = scored.candidate.approach_fit_score
  
        return matrix
  
    def _compute_hardware_fit(
        self, 
        candidate: ModelCandidate, 
        hardware: HardwareProfile
    ) -> float:
        """
        Compute how well the model fits the hardware.
        1.0 = runs comfortably with headroom
        0.5 = runs at minimum requirements
        0.0 = cannot run (should be filtered by Layer 1)
        
        Updated to factor in sustained performance ratio for laptops.
        See: docs/spec/HARDWARE_DETECTION.md Section 2
        """
        effective_vram = (
            hardware.ram_gb * 0.75 
            if hardware.unified_memory 
            else hardware.vram_gb
        )
  
        # Find best fitting variant
        best_fit = 0.0
        for variant in candidate.variants:
            required_vram = variant.vram_min_mb / 1024
            recommended_vram = variant.vram_recommended_mb / 1024
      
            if required_vram > effective_vram:
                continue  # Can't run this variant
      
            if effective_vram >= recommended_vram:
                fit = 1.0  # Comfortable headroom
            else:
                # Linear interpolation between min and recommended
                fit = 0.5 + 0.5 * (effective_vram - required_vram) / (recommended_vram - required_vram)
      
            best_fit = max(best_fit, fit)
  
        # Apply platform-specific penalties
        if hardware.platform == "apple_silicon":
            if candidate.mps_performance_penalty:
                best_fit *= (1.0 - candidate.mps_performance_penalty)
        
        # NEW: Apply sustained performance penalty for laptops
        if hardware.sustained_performance_ratio < 1.0:
            # Penalize compute-intensive models more on throttled hardware
            intensity = candidate.compute_intensity or "medium"
            if intensity == "high":
                # Full penalty for high-intensity models (video gen, large LLMs)
                best_fit *= hardware.sustained_performance_ratio
            elif intensity == "medium":
                # Partial penalty for medium-intensity
                best_fit *= (1.0 + hardware.sustained_performance_ratio) / 2
            # Low intensity models (small image gen) not penalized
  
        return best_fit
    
    def _compute_speed_fit(
        self,
        candidate: ModelCandidate,
        hardware: HardwareProfile,
        user_preferences: UserPreferences
    ) -> float:
        """
        NEW: Compute speed fit based on storage speed and model size.
        See: docs/spec/HARDWARE_DETECTION.md Section 4
        
        Returns:
            1.0 = fast loading (<5s)
            0.5 = moderate loading (5-30s)
            0.2 = slow loading (>60s)
        """
        # If user doesn't prioritize speed, give neutral score
        if user_preferences.speed_priority < 0.3:
            return 0.7  # Neutral-ish score
        
        # Estimate load time based on storage speed and model size
        model_size_gb = candidate.total_size_gb
        load_time_seconds = hardware.storage.estimate_load_time(model_size_gb)
        
        # Normalize load time to 0-1 score
        # <5s = 1.0 (excellent)
        # 5-15s = 0.8 (good)
        # 15-30s = 0.6 (acceptable)
        # 30-60s = 0.4 (slow)
        # >60s = 0.2 (very slow)
        if load_time_seconds <= 5:
            base_score = 1.0
        elif load_time_seconds <= 15:
            base_score = 0.8
        elif load_time_seconds <= 30:
            base_score = 0.6
        elif load_time_seconds <= 60:
            base_score = 0.4
        else:
            base_score = 0.2
        
        # Bonus for models that support fast inference (TensorRT, etc.)
        if candidate.supports_tensorrt and hardware.platform in ("windows_nvidia", "linux_nvidia"):
            base_score = min(1.0, base_score + 0.1)
        
        return base_score
```

### 6.5 Resolution Cascade

When hardware cannot run preferred models, apply resolution cascade:

```python
class ResolutionCascade:
    """
    When preferred model doesn't fit, find the best alternative.
    
    Updated to include CPU offload step.
    See: docs/spec/HARDWARE_DETECTION.md Section 5
    """
  
    RESOLUTION_ORDER = [
        'quantization_downgrade',
        'cpu_offload',              # NEW: Try CPU offload before substitution
        'variant_substitution',
        'workflow_optimization',
        'cloud_offload'
    ]
  
    def resolve(
        self,
        preferred_model: ModelCandidate,
        hardware: HardwareProfile,
        user_constraints: UserConstraints
    ) -> ResolutionResult:
        """
        Find the best way to run the preferred model or a suitable alternative.
        """
  
        # 1. Try quantization downgrade
        result = self._try_quantization_downgrade(preferred_model, hardware)
        if result.viable:
            return result
        
        # 2. NEW: Try CPU offload (model stays same, uses RAM for overflow)
        result = self._try_cpu_offload(preferred_model, hardware)
        if result.viable:
            return result
  
        # 3. Try variant substitution
        result = self._try_variant_substitution(preferred_model, hardware)
        if result.viable:
            return result
  
        # 4. Try workflow optimization
        result = self._try_workflow_optimization(preferred_model, hardware)
        if result.viable:
            return result
  
        # 4. Suggest cloud offload (if user allows)
        if user_constraints.cloud_willingness != 'local_only':
            result = self._suggest_cloud_offload(preferred_model, hardware)
            if result.viable:
                return result
  
        # No resolution found
        return ResolutionResult(
            viable=False,
            message=f"Cannot run {preferred_model.name} on your hardware. Consider upgrading to {preferred_model.recommended_vram_gb}GB VRAM."
        )
  
    def _try_quantization_downgrade(
        self, model: ModelCandidate, hardware: HardwareProfile
    ) -> ResolutionResult:
        """
        Try progressively lower quantization levels.
        FP16 → FP8 (if CC >= 8.9) → GGUF Q8 → Q6 → Q5 → Q4
        """
        effective_vram = hardware.vram_gb if not hardware.unified_memory else hardware.ram_gb * 0.75
  
        # Quantization preference order
        if hardware.supports_fp8:
            quant_order = ['fp16', 'fp8', 'gguf_q8', 'gguf_q6', 'gguf_q5', 'gguf_q4']
        elif hardware.platform == 'apple_silicon':
            # Non-K quants only for MPS
            quant_order = ['fp16', 'gguf_q8_0', 'gguf_q5_0', 'gguf_q4_0']
        else:
            quant_order = ['fp16', 'gguf_q8', 'gguf_q6', 'gguf_q5_k_m', 'gguf_q4_k_m']
  
        for quant in quant_order:
            variant = model.get_variant(quant)
            if variant and variant.vram_min_mb / 1024 <= effective_vram:
                quality_retention = variant.quality_retention_percent or 100
                return ResolutionResult(
                    viable=True,
                    resolution_type='quantization_downgrade',
                    selected_variant=variant,
                    message=f"Using {quant} quantization ({quality_retention}% quality retention)",
                    quality_impact=f"-{100 - quality_retention}% quality"
                )
  
        return ResolutionResult(viable=False)
    
    def _try_cpu_offload(
        self, model: ModelCandidate, hardware: HardwareProfile
    ) -> ResolutionResult:
        """
        NEW: Try running model with CPU offload when VRAM is insufficient.
        Offloads some layers to system RAM, slower but enables larger models.
        See: docs/spec/HARDWARE_DETECTION.md Section 5
        """
        # Model must support offloading
        if not model.supports_cpu_offload:
            return ResolutionResult(viable=False)
        
        # CPU must be adequate tier
        if hardware.cpu.tier not in (CPUTier.HIGH, CPUTier.MEDIUM):
            return ResolutionResult(
                viable=False,
                message=f"CPU ({hardware.cpu.tier.value}) insufficient for offload"
            )
        
        # Must have enough available RAM
        ram_needed = model.ram_for_offload_gb or model.min_vram_gb
        if hardware.ram.usable_for_offload_gb < ram_needed:
            return ResolutionResult(
                viable=False,
                message=f"Need {ram_needed:.1f}GB RAM, only {hardware.ram.usable_for_offload_gb:.1f}GB available"
            )
        
        # Calculate expected slowdown
        # HIGH tier CPU: ~5x slower, MEDIUM: ~10x slower
        slowdown_factor = 5 if hardware.cpu.tier == CPUTier.HIGH else 10
        
        return ResolutionResult(
            viable=True,
            resolution_type='cpu_offload',
            message=f"Can run {model.name} with CPU offload (~{slowdown_factor}x slower)",
            performance_factor=1.0 / slowdown_factor,
            quality_impact="Same quality, reduced speed"
        )
  
    def _try_variant_substitution(
        self, model: ModelCandidate, hardware: HardwareProfile
    ) -> ResolutionResult:
        """
        Substitute with a smaller variant in the same family.
        e.g., Wan 2.2 14B → Wan TI2V 5B → Wan 2.1 1.3B
        """
        substitutions = {
            'wan_22_14b': ['wan_ti2v_5b', 'wan_21_1.3b'],
            'flux_dev': ['flux_schnell'],
            'hunyuan_video': ['ltx_video_2b', 'animatediff'],
            'hidream_full': ['hidream_fast'],
        }
  
        family_subs = substitutions.get(model.family_id, [])
        for sub_id in family_subs:
            sub_model = self.model_db.get(sub_id)
            if sub_model and self._can_run(sub_model, hardware):
                return ResolutionResult(
                    viable=True,
                    resolution_type='variant_substitution',
                    substituted_model=sub_model,
                    message=f"Substituting {model.name} with {sub_model.name}",
                    quality_impact=f"Different model, similar capabilities"
                )
  
        return ResolutionResult(viable=False)
```

### 6.6 Explanation Generation

```python
class RecommendationExplainer:
    """
    Generate human-readable explanations for recommendations.
    """
  
    def explain_recommendation(
        self,
        ranked: RankedCandidate,
        rejections: List[RejectionReason],
        resolution: Optional[ResolutionResult]
    ) -> RecommendationExplanation:
        """
        Build complete explanation for why this model was recommended.
        """
        sections = []
  
        # Why selected
        sections.append(self._explain_selection(ranked))
  
        # Hardware fit
        sections.append(self._explain_hardware_fit(ranked))
  
        # Feature matches
        sections.append(self._explain_feature_matches(ranked))
  
        # If resolution was applied
        if resolution and resolution.resolution_type:
            sections.append(self._explain_resolution(resolution))
  
        # What was rejected and why
        if rejections:
            sections.append(self._explain_rejections(rejections[:3]))  # Top 3
  
        return RecommendationExplanation(
            summary=self._build_summary(ranked, resolution),
            sections=sections,
            confidence=ranked.topsis_score
        )
  
    def _build_summary(
        self, ranked: RankedCandidate, resolution: Optional[ResolutionResult]
    ) -> str:
        """One-sentence summary of recommendation."""
        model = ranked.candidate
  
        if resolution and resolution.resolution_type == 'quantization_downgrade':
            return f"Recommended: {model.name} ({resolution.selected_variant.precision}) - best match for your needs within your hardware limits"
        elif resolution and resolution.resolution_type == 'cloud_offload':
            return f"Recommended: {model.name} via cloud API - exceeds local hardware but matches your requirements"
        elif resolution and resolution.resolution_type == 'cpu_offload':
            return f"Recommended: {model.name} with CPU offload - runs slower but maintains full quality"
        else:
            return f"Recommended: {model.name} - strong match for your needs ({ranked.topsis_score:.0%} confidence)"
```

### 6.7 Hardware Integration Summary

This section summarizes how hardware detection (see `docs/spec/HARDWARE_DETECTION.md`) integrates with the recommendation engine.

#### 6.7.1 Hardware Elements by Layer

| Hardware Element | Layer 1 (CSP) | Layer 2 (Content) | Layer 3 (TOPSIS) | Resolution | Warnings |
|------------------|---------------|-------------------|------------------|------------|----------|
| **GPU VRAM** | ✅ `_check_vram_constraint` | - | ✅ `hardware_fit` | ✅ Quantization | - |
| **GPU Compute Capability** | ✅ `_check_compute_capability` | - | - | ✅ FP8→GGUF | - |
| **GPU Power/Form Factor** | - | - | ✅ `hardware_fit` penalty | - | ✅ Laptop warning |
| **Sustained Perf Ratio** | - | - | ✅ Intensity-based penalty | - | ✅ Throttle notice |
| **Platform (MPS/CUDA/ROCm)** | ✅ `_check_platform_constraint` | - | ✅ `mps_penalty` | - | - |
| **CPU Tier** | ✅ Offload viability | - | - | ✅ `_try_cpu_offload` | - |
| **CPU Cores** | ✅ Offload viability | - | - | ✅ Slowdown factor | - |
| **CPU AVX2** | ✅ GGUF offload check | - | - | - | ✅ Performance warning |
| **RAM Available** | ✅ `_check_ram_constraint` | - | - | ✅ Offload capacity | ✅ Low RAM warning |
| **RAM for Offload** | ✅ `_can_offload_to_cpu` | - | - | ✅ `_try_cpu_offload` | ✅ Offload active |
| **Storage Free Space** | ✅ `_check_storage_constraint` | - | - | ✅ `adjust_for_space` | - |
| **Storage Speed/Tier** | - | - | ✅ `speed_fit` | - | ✅ Speed warning |
| **Memory Bandwidth** | - | - | ✅ LLM tok/s estimate | - | - |

#### 6.7.2 TOPSIS Criteria Weights

**Default weights** (balanced user):
```python
{
    'content_similarity': 0.35,  # Feature match to user needs
    'hardware_fit': 0.25,        # VRAM headroom + platform penalties + form factor
    'speed_fit': 0.15,           # Storage speed + model load time
    'ecosystem_maturity': 0.15,  # Community support, documentation
    'approach_fit': 0.10,        # Workflow compatibility
}
```

**Speed-priority weights** (user prioritizes iteration speed):
```python
{
    'content_similarity': 0.25,
    'hardware_fit': 0.20,
    'speed_fit': 0.30,           # Elevated
    'ecosystem_maturity': 0.15,
    'approach_fit': 0.10,
}
```

#### 6.7.3 Resolution Cascade Order

```
1. Quantization Downgrade
   └─ FP16 → FP8 → GGUF Q8 → Q6 → Q5 → Q4
   
2. CPU Offload (NEW)
   └─ Requires: supports_cpu_offload + CPU tier HIGH/MEDIUM + sufficient RAM
   └─ Performance: ~5x slower (HIGH) or ~10x slower (MEDIUM)
   
3. Variant Substitution
   └─ e.g., Wan 14B → Wan 5B → Wan 1.3B
   
4. Workflow Optimization
   └─ Reduce batch size, resolution, etc.
   
5. Cloud Offload
   └─ Partner Nodes or third-party APIs
```

#### 6.7.4 Key Formulas

**Effective VRAM** (Apple Silicon):
```python
effective_vram = unified_memory_gb * 0.75
```

**Sustained Performance Ratio** (Laptop GPUs):
```python
performance_ratio = sqrt(actual_power_limit / reference_tdp)
```

**Storage Load Time Estimate**:
```python
load_time_seconds = model_size_gb * 1024 / storage_read_mbps
```

**Hardware Fit Score** (with form factor):
```python
if intensity == "high":
    fit *= sustained_performance_ratio
elif intensity == "medium":
    fit *= (1.0 + sustained_performance_ratio) / 2
```

#### 6.7.5 Space-Constrained Recommendation Adjustment

When total recommended models exceed available storage, apply priority-based fitting:

```python
def adjust_for_space(
    recommendations: List[Model],
    storage: StorageProfile,
    use_case_priorities: Dict[str, int]  # Lower = more important
) -> SpaceConstrainedResult:
    """
    Fit recommendations to available space by priority.
    See: docs/spec/HARDWARE_DETECTION.md Section 4.4
    """
    total_needed = sum(m.total_size_gb for m in recommendations)
    buffer_gb = 10  # Workspace reserve
    
    if storage.free_gb >= total_needed + buffer_gb:
        return SpaceConstrainedResult(fits=True, models=recommendations)
    
    # Sort by priority and greedily fit
    sorted_models = sorted(recommendations, 
        key=lambda m: use_case_priorities.get(m.use_case, 99))
    
    fitted, removed, cloud_fallback = [], [], []
    current_size = 0
    
    for model in sorted_models:
        if current_size + model.total_size_gb + buffer_gb <= storage.free_gb:
            fitted.append(model)
            current_size += model.total_size_gb
        else:
            removed.append(model)
            if model.cloud_available:
                cloud_fallback.append(model)
    
    return SpaceConstrainedResult(
        fits=False,
        models=fitted,
        removed=removed,
        cloud_alternatives=cloud_fallback,
        space_short_gb=total_needed - storage.free_gb + buffer_gb
    )
```

#### 6.7.6 Hardware Warnings for Explanation System

Generate user-facing warnings based on hardware constraints:

```python
def generate_hardware_warnings(
    hardware: HardwareProfile,
    user_preferences: UserPreferences,
    recommendations: List[Model]
) -> List[HardwareWarning]:
    """
    Generate warnings for the explanation system.
    See: docs/spec/HARDWARE_DETECTION.md
    """
    warnings = []
    
    # Laptop/form factor warning
    if hardware.is_laptop and hardware.sustained_performance_ratio < 0.8:
        warnings.append(HardwareWarning(
            type="form_factor",
            severity="info",
            title="Laptop GPU Detected",
            message=f"Your {hardware.gpu.name} runs at ~{hardware.sustained_performance_ratio*100:.0f}% "
                    "of desktop performance due to thermal constraints. "
                    "Long generation tasks may throttle further.",
            suggestions=["Keep laptop plugged in", "Ensure good ventilation"]
        ))
    
    # Storage speed warning (for speed-focused users)
    if user_preferences.speed_priority >= 0.7 and hardware.storage.tier == StorageTier.SLOW:
        largest_model = max(recommendations, key=lambda m: m.total_size_gb)
        load_time = hardware.storage.estimate_load_time(largest_model.total_size_gb)
        warnings.append(HardwareWarning(
            type="storage_speed",
            severity="warning",
            title="Storage Speed Notice",
            message=f"Your models are on HDD. Largest model ({largest_model.name}) "
                    f"will take ~{load_time:.0f}s to load.",
            suggestions=[
                "Install key models on SSD if available",
                "Use smaller quantized variants",
                "Minimize model switching"
            ]
        ))
    
    # CPU offload warning (when being used)
    offload_models = [m for m in recommendations if m.execution_mode == "gpu_offload"]
    if offload_models:
        slowdown = 5 if hardware.cpu.tier == CPUTier.HIGH else 10
        warnings.append(HardwareWarning(
            type="cpu_offload",
            severity="info",
            title="CPU Offload Active",
            message=f"{len(offload_models)} model(s) will use CPU offload (~{slowdown}x slower): "
                    + ", ".join(m.name for m in offload_models[:3]),
            suggestions=["Consider cloud alternatives for faster inference"]
        ))
    
    # Low RAM warning for offload-dependent configs
    if hardware.ram.usable_for_offload_gb < 16 and any(
        m.execution_mode == "gpu_offload" for m in recommendations
    ):
        warnings.append(HardwareWarning(
            type="ram_limited",
            severity="warning",
            title="Limited RAM for Offload",
            message=f"Only {hardware.ram.usable_for_offload_gb:.0f}GB RAM available for offload. "
                    "Some models may fail to load.",
            suggestions=["Close other applications", "Use smaller model variants"]
        ))
    
    # AVX warning for GGUF on old CPUs
    gguf_models = [m for m in recommendations 
                   if any('gguf' in v.precision for v in m.variants)]
    if gguf_models and not hardware.cpu.supports_avx2:
        warnings.append(HardwareWarning(
            type="cpu_features",
            severity="warning",
            title="Limited CPU Features",
            message="Your CPU lacks AVX2 support. GGUF model inference will be significantly slower.",
            suggestions=["Consider FP16 variants instead", "Use cloud APIs"]
        ))
    
    return warnings
```

#### 6.7.7 Memory Bandwidth Impact (Apple Silicon LLMs)

For LLM inference on Apple Silicon, memory bandwidth is the primary bottleneck:

```python
def estimate_llm_tokens_per_second(
    model_params_b: float,
    hardware: HardwareProfile
) -> float:
    """
    Estimate LLM inference speed based on memory bandwidth.
    Only applicable for Apple Silicon unified memory.
    
    Formula: tokens/sec ≈ bandwidth_gbps / (2 * params_b)
    (Assumes ~2 bytes per parameter access per token)
    """
    if not hardware.gpu.unified_memory:
        return None  # NVIDIA uses different bottleneck
    
    bandwidth = hardware.gpu.memory_bandwidth_gbps
    bytes_per_param = 2  # FP16 or GGUF average
    
    tokens_per_sec = bandwidth / (bytes_per_param * model_params_b)
    return tokens_per_sec

# Example impact:
# M1 (68 GB/s) + 7B model = 68 / (2 * 7) = ~4.8 tok/s
# M4 Max (546 GB/s) + 7B model = 546 / (2 * 7) = ~39 tok/s
# M4 Max (546 GB/s) + 70B model = 546 / (2 * 70) = ~3.9 tok/s
```

This can inform:
- Model variant selection (smaller = faster on bandwidth-limited systems)
- User expectations for LLM-based workflows
- Trade-off explanations in the recommendation system

---

## 7. Model Database Schema

### 7.1 Overview

The model database (`data/models_database.yaml`) contains all supported models with their variants, capabilities, and hardware requirements. The recommendation engine queries this database during Layer 1 (constraint satisfaction) and Layer 2 (content-based filtering).

### 7.2 Schema Definition

```yaml
# Model entry schema
{model_id}:
  # === IDENTIFICATION ===
  name: string                  # Display name
  family: string                # Model family (flux, wan, sdxl, etc.)
  release_date: string          # ISO date
  
  # === LICENSING ===
  license: string               # "mit", "apache-2.0", "non-commercial", "community"
  commercial_use: boolean
  
  # === ARCHITECTURE ===
  architecture:
    type: string                # "dit", "moe_dit", "unet", "transformer"
    parameters_b: float         # Billions of parameters
    text_encoder: string        # "t5_xxl", "clip", "t5_umt5", etc.
    vae: string                 # VAE identifier
    notes: string               # Architecture-specific notes
  
  # === VARIANTS ===
  variants:
    - id: string                # "fp16", "fp8", "gguf_q8", "gguf_q4", etc.
      precision: string         # Precision format
      vram_min_mb: int          # Minimum VRAM in MB
      vram_recommended_mb: int  # Recommended VRAM in MB
      download_url: string      # Primary download URL
      download_size_gb: float   # Download size
      quality_retention_percent: int  # Quality vs FP16 baseline
      platform_support:
        windows_nvidia: {supported: bool, min_compute_capability: float}
        mac_mps: {supported: bool, notes: string}
        linux_rocm: {supported: bool}
      requires_nodes: list      # Required custom nodes for this variant
  
  # === CAPABILITIES ===
  capabilities:
    primary: list               # ["text_to_image", "image_to_video", etc.]
    video_modes: list           # ["t2v", "i2v", "flf2v"] for video models
    max_duration_seconds: int   # For video models
    max_resolution: string      # "720p", "1080p", "4k"
    audio_support: boolean      # Native audio generation
    scores:
      photorealism: float       # 0-1
      artistic_quality: float
      text_rendering: float
      motion_quality: float     # For video
      temporal_coherence: float # For video
      speed: float
      consistency: float
    features:
      - id: string
        quality: string         # "excellent", "good", "limited"
        notes: string
    style_strengths: list       # ["photorealistic", "anime", "cinematic"]
    controlnet_support: list    # ["depth", "canny", "pose", "lineart"]
  
  # === DEPENDENCIES ===
  dependencies:
    required_nodes:
      - package: string         # Node package name
        repo: string            # Git repository URL
        required_for: list      # Which variants need this
    paired_models:
      - model_id: string        # Companion model ID
        reason: string          # Why pairing is needed
    incompatibilities: list     # Known incompatible configurations
  
  # === CLOUD AVAILABILITY ===
  cloud:
    partner_node: boolean       # Available via ComfyUI Partner Nodes
    partner_service: string     # "veo", "kling", "luma", "runway", etc.
    replicate: boolean
    fal_ai: boolean
    estimated_cost_per_generation: float
  
  # === HARDWARE INTEGRATION (NEW) ===
  # See: docs/spec/HARDWARE_DETECTION.md
  hardware:
    total_size_gb: float        # Total disk space needed (all files)
    compute_intensity: string   # "high", "medium", "low" - affects laptop penalty
    supports_cpu_offload: boolean  # Can offload layers to RAM
    ram_for_offload_gb: float   # RAM needed if using CPU offload
    supports_tensorrt: boolean  # TensorRT optimization available
    mps_performance_penalty: float  # 0.0-1.0, penalty on Apple Silicon
  
  # === EXPLANATION TEMPLATES ===
  explanation:
    selected: string            # Why this was recommended
    rejected_vram: string       # Template when rejected for VRAM
    rejected_platform: string   # Template when rejected for platform
```

### 7.3 Model Family Summary

Based on comprehensive research, here are the model families the database must cover:

#### 7.3.1 Image Generation Models

| Model             | Parameters | FP16 VRAM | FP8 VRAM | GGUF Q4 | License        | Key Capability                    |
| ----------------- | ---------- | --------- | -------- | ------- | -------------- | --------------------------------- |
| HiDream-I1 Full   | 17B        | 48GB      | 24GB     | ~10GB   | MIT            | Highest quality, hybrid DiT+MoE   |
| HiDream-I1 Fast   | 17B        | 27GB      | 16GB     | ~10GB   | MIT            | Speed-optimized                   |
| Z-Image-Turbo     | 6B         | 16GB      | 8GB      | N/A     | Apache 2.0     | Sub-second, bilingual text        |
| Ovis-Image        | 7B         | 16GB      | N/A      | N/A     | Apache 2.0     | Best text accuracy (0.92 CVTG-2K) |
| Chroma1-HD        | 8.9B       | 24GB      | N/A      | ~8GB    | Apache 2.0     | Commercial-safe Flux alternative  |
| FLUX.1-Dev        | 12B        | 33GB      | 12GB     | ~8GB    | Non-commercial | Quality benchmark                 |
| FLUX.1-Schnell    | 12B        | 24GB      | 12GB     | ~6GB    | Apache 2.0     | Fast iteration                    |
| SD3.5 Large       | 8B         | 20GB      | 12GB     | N/A     | Community      | Good text rendering               |
| SD3.5 Medium      | 2.6B       | 8GB       | N/A      | N/A     | Community      | Entry point with text             |
| Playground v2.5   | 3.5B       | 12GB      | N/A      | N/A     | Community      | Strong aesthetics                 |
| Kolors            | 7B         | 13GB      | 8GB      | ~4GB    | Academic       | Bilingual (EN/ZH)                 |
| PixArt-Σ         | 600M+T5    | 20GB      | 6GB      | N/A     | Non-commercial | Direct 4K generation              |
| SDXL (ecosystem)  | 3.5B       | 12GB      | 8GB      | ~6GB    | Various        | Largest ecosystem                 |
| SD1.5 (ecosystem) | 1B         | 6GB       | N/A      | N/A     | Various        | 10,000+ fine-tunes                |

#### 7.3.2 Image Editing Models

| Model                | Parameters | FP16 VRAM | FP8 VRAM  | GGUF Q4   | Key Capability                 |
| -------------------- | ---------- | --------- | --------- | --------- | ------------------------------ |
| ChronoEdit 14B       | 14B        | 34-38GB   | Available | Available | Physics-aware temporal editing |
| Qwen-Image-Edit 2511 | 20B        | 40GB      | 16GB      | ~12GB     | Multi-person, text editing     |
| Qwen-Image-Layered   | 20B        | 40GB      | 16GB      | Available | RGBA layer decomposition       |
| OmniGen2             | 7B         | 17GB      | N/A       | N/A       | Instruction-based, multi-image |
| OmniGen v1           | 3.8B       | 15.5GB    | Available | N/A       | Multi-reference editing        |
| ICEdit               | ~200M LoRA | 14GB      | N/A       | N/A       | Mask-based, 4GB with Nunchaku  |
| Step1X-Edit          | Large      | 46GB      | 31GB      | N/A       | 11 edit categories             |
| FLUX.1 Fill          | 12B        | 24GB      | Available | ~8GB      | Inpainting/outpainting         |

#### 7.3.3 Video Generation Models - Wan Family

| Variant             | Purpose             | FP16 VRAM   | FP8 VRAM | Q8 GGUF  | Q4 GGUF         |
| ------------------- | ------------------- | ----------- | -------- | -------- | --------------- |
| Wan 2.2 T2V 14B     | Text-to-video       | ~60GB total | ~28GB    | 15.4GB   | 9.6GB           |
| Wan 2.2 I2V 14B     | Image-to-video      | ~57GB total | ~28GB    | 15.4GB   | 9.6GB           |
| Wan 2.2 TI2V 5B     | Hybrid T2V+I2V      | 10GB        | 5-6GB    | 5.4GB    | **3.4GB** |
| Wan 2.2 FLF2V 14B   | First-last frame    | Uses I2V    | Uses I2V | Uses I2V | Uses I2V        |
| Wan 2.2 Fun Camera  | Camera control      | ~32GB       | 14-15GB  | N/A      | N/A             |
| Wan 2.2 Fun Control | Pose/depth/canny    | ~32GB       | 14-16GB  | N/A      | N/A             |
| Wan 2.2 Fun Inpaint | Video inpainting    | ~32GB       | 14-16GB  | N/A      | N/A             |
| Wan 2.2 Animate     | Character animation | ~32GB       | 16-18GB  | 18.7GB   | 11.5GB          |
| Wan 2.2 S2V         | Speech-to-video     | 32.6GB      | 16.4GB   | 19.6GB   | 13.9GB          |
| Wan 2.1 T2V 14B     | High quality        | 28GB        | 14GB     | N/A      | N/A             |
| Wan 2.1 T2V 1.3B    | Consumer GPU        | 8.2GB       | 4-5GB    | N/A      | N/A             |

**Critical Note**: Wan TI2V 5B at 3.4GB GGUF Q4 is the breakthrough for consumer hardware - full T2V+I2V on any modern GPU.

#### 7.3.4 Other Video Models

| Model            | Parameters | Min VRAM  | Recommended | T2V | I2V            | FLF2V | Audio |
| ---------------- | ---------- | --------- | ----------- | --- | -------------- | ----- | ----- |
| HunyuanVideo 1.5 | 8.3B       | 8GB GGUF  | 24GB        | ✅  | ❌             | ❌    | ❌    |
| HunyuanVideo-I2V | 13B        | 12GB GGUF | 60GB        | ❌  | ✅             | ❌    | ❌    |
| LTX-Video 2B     | 2B         | 6GB       | 10GB        | ✅  | ✅             | ✅    | ✅    |
| LTX-Video 13B    | 13B        | 10GB      | 24GB        | ✅  | ✅             | ✅    | ✅    |
| CogVideoX-2B     | 2B         | 6GB       | 8GB         | ✅  | ❌             | ❌    | ❌    |
| CogVideoX-5B     | 5B         | 12GB      | 16GB        | ✅  | ✅             | ❌    | ❌    |
| Mochi 1          | 10B        | 12GB      | 24GB        | ✅  | Via encoder    | ❌    | ❌    |
| AnimateDiff      | Module     | 6GB       | 10GB        | ✅  | Via ControlNet | ❌    | ❌    |

#### 7.3.5 Audio Generation Models

| Model             | Type         | Parameters | VRAM        | Voice Clone       | Languages  | License         |
| ----------------- | ------------ | ---------- | ----------- | ----------------- | ---------- | --------------- |
| F5-TTS            | TTS/Clone    | ~1.2GB     | 6GB         | ✅ (5-15s sample) | 9+         | Apache 2.0      |
| Kokoro TTS        | TTS          | 82M        | CPU-capable | ❌ (54 presets)   | 9          | Apache 2.0      |
| XTTS v2           | TTS/Clone    | N/A        | 4-8GB       | ✅ (6s sample)    | 17         | CPML            |
| Bark              | TTS/SFX      | ~1B        | 8-12GB      | ⚠️ Limited      | 13+        | MIT             |
| MusicGen          | Music        | 300M-3.3B  | 8-16GB      | N/A               | EN prompts | CC-BY-NC        |
| ACE-Step          | Music/Vocals | 3.5B       | 8-16GB      | ✅                | Multi      | Apache 2.0      |
| Stable Audio Open | Music/SFX    | ~4.7GB     | 8-12GB      | N/A               | EN         | Commercial-safe |

#### 7.3.6 3D Generation Models

| Model            | Parameters  | Min VRAM  | Full Pipeline | Output             | License    |
| ---------------- | ----------- | --------- | ------------- | ------------------ | ---------- |
| Hunyuan3D 2-mini | 0.6B shape  | 5GB       | 8GB           | GLB with PBR       | Open       |
| Hunyuan3D 2.1    | 3.3B + 1.3B | 6GB shape | 24GB          | GLB with PBR       | Open       |
| TRELLIS.2        | 4B          | 8GB       | 24GB          | Mesh/Gaussians/PBR | MIT        |
| TripoSR          | ~300M       | 7GB       | 8GB           | UV-unwrapped mesh  | MIT        |
| InstantMesh      | ~1B         | 10GB      | 12GB          | Textured mesh      | Apache 2.0 |

#### 7.3.7 Lip Sync Models

| Model          | Parameters  | Min VRAM | Recommended | Input                 | Quality            |
| -------------- | ----------- | -------- | ----------- | --------------------- | ------------------ |
| Wav2Lip        | ~100M       | 4GB      | 6GB         | Video + 16kHz audio   | Good               |
| LatentSync 1.6 | ~5GB models | 6.5GB    | 20GB        | Video + audio         | High (512×512)    |
| SadTalker      | Multiple    | 6GB      | 8GB         | Image + audio         | Realistic motion   |
| LivePortrait   | Multiple    | 8GB      | 12GB        | Image + driving video | Facial reenactment |
| HuMo 1.7B      | 1.7B        | 10GB     | 16GB        | Text/image/audio      | Multimodal         |

### 7.4 VRAM Tier Quick Reference

| VRAM            | Image                              | Video                     | 3D                 | Audio          |
| --------------- | ---------------------------------- | ------------------------- | ------------------ | -------------- |
| **6-8GB** | SD3.5 Medium, Z-Image FP8, Flux Q4 | Wan TI2V 5B Q4, LTX 2B    | Hunyuan3D mini     | F5-TTS, Kokoro |
| **12GB**  | FLUX Dev FP8, HiDream Q4           | Wan 2.1 14B Q4, CogVideoX | TripoSR            | All TTS        |
| **24GB**  | All FP8                            | Wan 2.2 FP8, HunyuanVideo | Hunyuan3D 2.1 full | ACE-Step       |
| **48GB+** | All FP16                           | Wan 2.2 FP16, HuMo 14B    | TRELLIS.2 max      | Production     |

---

## 8. Cloud API Integration

### 8.1 Architecture Overview

Cloud API integration uses **ComfyUI's Partner Node system** as the primary mechanism, with support for third-party APIs via key management.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  AI Universal Suite                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Cloud API Manager                                               │    │
│  │  • Partner Node account status                                   │    │
│  │  • Third-party API key storage                                   │    │
│  │  • Cost estimation display                                       │    │
│  │  • Fallback routing logic                                        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                    │                           │
                    ▼                           ▼
┌───────────────────────────────┐  ┌───────────────────────────────────┐
│  Partner Nodes (Unified)      │  │  Third-Party APIs (Key-based)    │
│  ─────────────────────────────│  │  ─────────────────────────────── │
│  • Single ComfyUI account     │  │  • Replicate                     │
│  • Unified credit balance     │  │  • fal.ai                        │
│  • No individual API keys     │  │  • RunPod                        │
│  │                            │  │  • Custom endpoints              │
│  │  Services:                 │  │                                   │
│  │  • Google Veo 2/3/3.1      │  │  Keys stored in:                 │
│  │  • Kling 2.0/1.6/1.5       │  │  ComfyUI/keys/{provider}.txt     │
│  │  • Luma Ray 2/3            │  │                                   │
│  │  • Runway Gen3a/Gen4       │  └───────────────────────────────────┘
│  │  • OpenAI Sora 2           │
│  │  • MiniMax/Hailuo          │
│  │  • BFL FLUX Pro            │
│  │  • Stability Ultra         │
│  │  • Ideogram V3             │
│  │  • Recraft V3              │
│  └────────────────────────────┘
```

### 8.2 Partner Node Integration

#### 8.2.1 Account Linking

Partner Nodes use the ComfyUI account system. Users link their account once and purchase credits through comfy.org.

```python
class PartnerNodeManager:
    """
    Manage Partner Node account status and capabilities.
    """
  
    def check_account_status(self) -> PartnerNodeStatus:
        """
        Check if ComfyUI account is linked and has credits.
        """
        # Check for ComfyUI account token
        token_path = Path.home() / ".comfyui" / "account_token"
        if not token_path.exists():
            return PartnerNodeStatus(
                linked=False,
                message="ComfyUI account not linked. Link at comfy.org to use cloud APIs."
            )
  
        # Verify token and get balance
        try:
            balance = self._fetch_credit_balance(token_path.read_text())
            return PartnerNodeStatus(
                linked=True,
                credit_balance=balance,
                available_services=self._get_available_services()
            )
        except AuthError:
            return PartnerNodeStatus(
                linked=False,
                message="Account token expired. Please re-link at comfy.org"
            )
  
    def _get_available_services(self) -> List[PartnerService]:
        """List all available Partner Node services."""
        return [
            PartnerService(
                id="veo",
                name="Google Veo",
                versions=["2", "3", "3.1", "fast"],
                capabilities=["t2v", "i2v", "flf2v", "camera_control", "audio"],
                max_duration=8,
            ),
            PartnerService(
                id="kling",
                name="Kling",
                versions=["2.0", "1.6", "1.5", "O1"],
                capabilities=["t2v", "i2v", "flf2v", "camera_control", "dual_character", "lip_sync"],
                max_duration=10,
            ),
            PartnerService(
                id="luma_ray",
                name="Luma Ray",
                versions=["3", "2", "flash-2"],
                capabilities=["t2v", "i2v", "keyframes", "camera_control", "audio", "4k_hdr"],
                max_duration=10,
            ),
            PartnerService(
                id="runway",
                name="Runway",
                versions=["Gen3a", "Gen4 Turbo"],
                capabilities=["t2v", "i2v", "flf2v", "image_refs"],
                max_duration=10,
            ),
            PartnerService(
                id="sora",
                name="OpenAI Sora",
                versions=["2", "2 Pro"],
                capabilities=["t2v", "i2v", "audio"],
                max_duration=12,
            ),
            PartnerService(
                id="minimax",
                name="MiniMax/Hailuo",
                versions=["Hailuo-02", "S2V-01"],
                capabilities=["t2v", "i2v", "flf2v", "subject_ref"],
                max_duration=10,
            ),
        ]
```

#### 8.2.2 Video API Capabilities Matrix

| Service               | T2V | I2V | FLF2V        | Camera      | Character Ref | Lip Sync | Audio     | Max Duration |
| --------------------- | --- | --- | ------------ | ----------- | ------------- | -------- | --------- | ------------ |
| **Veo 3.1**     | ✅  | ✅  | ✅           | ✅          | Via prompts   | ❌       | ✅ Native | 8 sec        |
| **Kling 2.0**   | ✅  | ✅  | ✅           | ✅ Full     | Dual refs     | ✅       | ❌        | 10 sec       |
| **Luma Ray 3**  | ✅  | ✅  | ✅ Keyframes | ✅          | Image refs    | ❌       | ✅        | 10 sec       |
| **Runway Gen4** | ✅  | ✅  | ✅           | Via prompts | Image refs    | ❌       | ❌        | 10 sec       |
| **Sora 2**      | ✅  | ✅  | ❌           | ❌          | Via prompts   | ❌       | ✅ Native | 12 sec       |
| **MiniMax**     | ✅  | ✅  | ✅           | Via prompts | S2V-01 only   | ❌       | ❌        | 10 sec       |

#### 8.2.3 Image API Pricing (Approximate)

| Service   | Model                | Approximate Cost/Image |
| --------- | -------------------- | ---------------------- |
| BFL       | FLUX Pro             | ~$0.04                 |
| BFL       | FLUX Pro Ultra (4MP) | ~$0.06                 |
| OpenAI    | GPT-Image-1          | $0.02-0.08             |
| OpenAI    | DALL·E 3 HD         | ~$0.04-0.12            |
| Stability | Ultra                | ~$0.08                 |
| Ideogram  | V3                   | ~$0.08                 |
| Recraft   | V3                   | ~$0.04                 |

**Note**: Midjourney has no official API - only third-party proxy services exist.

### 8.3 Third-Party API Key Management

For APIs not covered by Partner Nodes:

```python
class ThirdPartyAPIManager:
    """
    Manage third-party API keys stored in ComfyUI/keys/ folder.
    """
  
    SUPPORTED_PROVIDERS = {
        "replicate": {
            "key_file": "replicate.txt",
            "env_var": "REPLICATE_API_TOKEN",
            "signup_url": "https://replicate.com/account/api-tokens",
        },
        "fal_ai": {
            "key_file": "fal.txt",
            "env_var": "FAL_KEY",
            "signup_url": "https://fal.ai/dashboard/keys",
        },
        "runpod": {
            "key_file": "runpod.txt",
            "env_var": "RUNPOD_API_KEY",
            "signup_url": "https://www.runpod.io/console/user/settings",
        },
    }
  
    def __init__(self, comfyui_path: Path):
        self.keys_dir = comfyui_path / "keys"
        self.keys_dir.mkdir(exist_ok=True)
  
    def set_api_key(self, provider: str, api_key: str) -> None:
        """
        Store API key for provider.
        Writes to ComfyUI/keys/{provider}.txt
        """
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")
  
        key_file = self.keys_dir / self.SUPPORTED_PROVIDERS[provider]["key_file"]
        key_file.write_text(api_key.strip())
  
        # Also set environment variable for current session
        env_var = self.SUPPORTED_PROVIDERS[provider]["env_var"]
        os.environ[env_var] = api_key.strip()
  
    def get_api_key(self, provider: str) -> Optional[str]:
        """Retrieve stored API key."""
        if provider not in self.SUPPORTED_PROVIDERS:
            return None
  
        key_file = self.keys_dir / self.SUPPORTED_PROVIDERS[provider]["key_file"]
        if key_file.exists():
            return key_file.read_text().strip()
        return None
  
    def list_configured_providers(self) -> List[str]:
        """List providers with configured API keys."""
        configured = []
        for provider, config in self.SUPPORTED_PROVIDERS.items():
            key_file = self.keys_dir / config["key_file"]
            if key_file.exists() and key_file.read_text().strip():
                configured.append(provider)
        return configured
```

### 8.4 Cloud Offload Decision Framework

```python
class CloudOffloadStrategy:
    """
    Determine when to suggest cloud APIs vs local execution.
    """
  
    def should_suggest_cloud(
        self,
        model: ModelCandidate,
        hardware: HardwareProfile,
        user_constraints: UserConstraints,
        partner_status: PartnerNodeStatus
    ) -> CloudSuggestion:
        """
        Evaluate whether cloud execution should be suggested.
        """
  
        # User explicitly wants local only
        if user_constraints.cloud_willingness == 'local_only':
            return CloudSuggestion(suggest=False)
  
        # Check if model can run locally
        can_run_locally = self._can_run_locally(model, hardware)
  
        # If can run locally and user prefers local, don't suggest cloud
        if can_run_locally and user_constraints.cloud_willingness == 'cloud_fallback':
            return CloudSuggestion(suggest=False)
  
        # Check cloud availability
        if not model.cloud_available:
            if not can_run_locally:
                return CloudSuggestion(
                    suggest=False,
                    message=f"{model.name} exceeds your hardware and has no cloud option available."
                )
            return CloudSuggestion(suggest=False)
  
        # Check if Partner Node account is linked
        if not partner_status.linked:
            return CloudSuggestion(
                suggest=True,
                requires_setup=True,
                message="Link your ComfyUI account to use cloud APIs",
                setup_url="https://comfy.org/account"
            )
  
        # Calculate cost estimate
        cost_estimate = self._estimate_cost(model)
  
        # Determine suggestion based on user preference
        if user_constraints.cloud_willingness == 'cloud_preferred':
            return CloudSuggestion(
                suggest=True,
                service=model.partner_service,
                estimated_cost=cost_estimate,
                message=f"Using {model.partner_service} (~${cost_estimate:.2f}/generation)"
            )
  
        # cloud_fallback: suggest only if can't run locally
        if not can_run_locally:
            return CloudSuggestion(
                suggest=True,
                service=model.partner_service,
                estimated_cost=cost_estimate,
                message=f"{model.name} requires {model.min_vram_gb}GB VRAM. Suggesting cloud execution (~${cost_estimate:.2f}/generation)"
            )
  
        return CloudSuggestion(suggest=False)
```

### 8.5 Cost Display Integration

When recommending cloud-based models, display cost estimates:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Recommended: Kling 2.0 via Cloud API                                   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ⚡ Why cloud: Kling 2.0 requires 24GB+ VRAM for local          │   │
│  │     execution. Your system has 8GB.                             │   │
│  │                                                                  │   │
│  │  💰 Estimated cost: ~$0.15 per 10-second video                  │   │
│  │                                                                  │   │
│  │  ✨ Capabilities: T2V, I2V, camera control, dual character      │   │
│  │     consistency, lip sync                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  [Use Cloud]          [Try Local Anyway (Wan TI2V 5B)]                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.6 Hybrid Workflow Strategy

For production workflows, recommend hybrid local+cloud:

```python
HYBRID_WORKFLOW_RECOMMENDATIONS = {
    "video_production": {
        "local_phase": {
            "purpose": "Iteration and previews",
            "models": ["wan_ti2v_5b", "ltx_video_2b"],
            "rationale": "Fast local iteration for concept development"
        },
        "cloud_phase": {
            "purpose": "Final renders",
            "services": ["veo_3", "kling_2"],
            "rationale": "Highest quality for deliverables"
        }
    },
    "image_production": {
        "local_phase": {
            "purpose": "Exploration and refinement",
            "models": ["flux_schnell_gguf", "sdxl"],
            "rationale": "Unlimited local iterations"
        },
        "cloud_phase": {
            "purpose": "Final high-resolution",
            "services": ["flux_pro_ultra"],
            "rationale": "4MP output for print/production"
        }
    }
}
```

---

## 9. User Flow

### 9.1 First Launch Flow

```
Application Start
       │
       ▼
┌──────────────────┐
│ Check first_run  │
│ flag in config   │
└────────┬─────────┘
         │
    ┌────┴────┐
    │ First   │
    │ Launch? │
    └────┬────┘
     Yes │        No
         ▼         ▼
┌─────────────────┐  ┌─────────────────┐
│ Show Path       │  │ Show Main       │
│ Selection       │  │ Dashboard       │
│ (Quick/Comp.)   │  │                 │
└─────────────────┘  └─────────────────┘
```

### 9.2 Setup Wizard Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SETUP WIZARD STAGES                                │
└─────────────────────────────────────────────────────────────────────────┘

Stage 0: Path Selection
├── Display: Quick Setup vs Comprehensive Setup cards
├── Input: Path selection
└── Action: [Continue]

       │
       ▼

Stage 1: Hardware Detection (Automatic)
├── Display: Scanning animation (2-3 seconds)
├── Detect: GPU, VRAM, RAM, Storage, Platform
├── Output: Hardware confirmation screen
├── Action: [This looks right] or [Edit hardware info]
└── Skip: Not available

       │
       ▼

Stage 2: Onboarding Questions
├── Quick Path: 5 questions on single flow
├── Comprehensive Path: Tiered progressive (Tier 1-6)
├── Display: Progress indicator, running recommendation preview
├── Action: [Next] per question, [Skip] where allowed
└── Validation: Required fields must be answered

       │
       ▼

Stage 3: Recommendation Review
├── Display:
│   ├── Recommended configuration summary
│   ├── Model list with VRAM requirements
│   ├── Total download size
│   ├── Estimated installation time
│   ├── Reasoning for each recommendation
│   └── Warnings (if any)
├── Actions: [Customize] [Accept & Install]
└── Customize opens detailed model selection

       │
       ▼

Stage 4: Installation
├── Display:
│   ├── Overall progress bar
│   ├── Current task indicator
│   ├── Per-item progress bars
│   └── Log output (collapsible)
├── Process:
│   ├── Install dependencies (Git, Python if missing)
│   ├── Clone ComfyUI repository
│   ├── Install ComfyUI Manager
│   ├── Clone required custom nodes
│   ├── Download models (with progress)
│   ├── Configure environments
│   ├── Validate installations
│   └── Create desktop shortcuts
├── Error Handling:
│   ├── Retry failed downloads (3 attempts, exponential backoff)
│   ├── Show clear error messages
│   └── Allow [Retry] or [Skip This Item]
└── Actions: [Cancel] (with confirmation)

       │
       ▼

Stage 5: Complete
├── Display:
│   ├── Success message
│   ├── List of installed tools with status
│   ├── List of created shortcuts
│   └── Quick start tips
├── Actions: [Open Dashboard] [Launch ComfyUI] [Close]
└── Side Effect: Set first_run = false in config
```

### 9.3 Post-Setup Dashboard

```
┌─────────────────────────────────────────────────────────────────────────┐
│  AI Universal Suite                                    [Settings] [?]   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐             │
│  │  Overview   │  ComfyUI    │  Models     │  Cloud APIs │             │
│  └─────────────┴─────────────┴─────────────┴─────────────┘             │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  OVERVIEW                                                        │   │
│  │                                                                  │   │
│  │  System Status: ✅ Ready                                         │   │
│  │  Hardware: RTX 4090 (24GB) • 64GB RAM • 500GB free              │   │
│  │                                                                  │   │
│  │  ┌──────────────────┐  ┌──────────────────┐                     │   │
│  │  │  🎨 ComfyUI      │  │  🤖 Claude CLI   │                     │   │
│  │  │  Ready           │  │  Ready           │                     │   │
│  │  │  [Launch]        │  │  [Open Terminal] │                     │   │
│  │  └──────────────────┘  └──────────────────┘                     │   │
│  │                                                                  │   │
│  │  Recent Activity:                                                │   │
│  │  • Installed Wan 2.2 I2V Q5 (2 hours ago)                       │   │
│  │  • Generated 47 images today                                     │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.4 Model Manager View

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Models                                              [+ Add Model]      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Filter: [All ▼] [Image ▼] [Video ▼]    Search: [____________]         │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  INSTALLED MODELS                                                │   │
│  │                                                                  │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │  Wan 2.2 I2V 14B (Q5)                                    │   │   │
│  │  │  Video Generation • 9.8GB × 2 = 19.6GB                   │   │   │
│  │  │  ✅ Both experts installed                               │   │   │
│  │  │  [Delete] [Update]                                       │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  │                                                                  │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │  FLUX.1 Schnell (GGUF Q5)                                │   │   │
│  │  │  Image Generation • 8.2GB                                │   │   │
│  │  │  [Delete] [Update]                                       │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  RECOMMENDED FOR YOU                                             │   │
│  │                                                                  │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │  HiDream-I1 Fast (GGUF Q4)                               │   │   │
│  │  │  Image Generation • ~10GB • Fits your hardware ✅        │   │   │
│  │  │  "Highest quality image generation for your VRAM"        │   │   │
│  │  │  [Install]                                               │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Data Schemas

### 10.1 Configuration Schema (`config.json`)

```json
{
  "version": "3.0",
  "first_run": true,
  "wizard_completed": false,
  "wizard_version": "3.0",
  "wizard_path": "comprehensive",
  
  "user_profile": {
    "use_cases": ["images", "video"],
    "experience_level": "regular",
    "priority_slider": 0.6,
    "cloud_willingness": "cloud_fallback",
  
    "image_preferences": {
      "styles": ["photorealistic", "cinematic"],
      "editing_needs": ["inpainting", "instruction_editing"],
      "text_rendering": "occasional",
      "character_consistency": "helpful"
    },
  
    "video_preferences": {
      "modes": ["i2v", "flf2v"],
      "duration": "short",
      "audio_sync": ["lip_sync"],
      "camera_control": "basic"
    },
  
    "workflow_preferences": {
      "complexity_tolerance": "moderate",
      "budget_sensitivity": "balanced"
    }
  },
  
  "factor_scores": {
    "quality_priority": 0.7,
    "speed_priority": 0.5,
    "control_priority": 0.6,
    "consistency_priority": 0.5,
    "simplicity_priority": 0.4
  },
  
  "hardware_profile": {
    "platform": "windows_nvidia",
    "gpu_vendor": "nvidia",
    "gpu_name": "NVIDIA GeForce RTX 4090",
    "vram_gb": 24,
    "ram_gb": 64,
    "compute_capability": 8.9,
    "storage_type": "nvme",
    "disk_free_gb": 500
  },
  
  "progressive_disclosure": {
    "session_count": 0,
    "advanced_settings_visible": false,
    "calibration_prompt_shown": false
  },
  
  "paths": {
    "comfyui": "~/ComfyUI",
    "models": "~/ComfyUI/models",
    "shortcuts": "~/Desktop"
  },
  
  "modules": {
    "comfyui": {
      "enabled": true,
      "installed": true,
      "version": "0.3.60",
      "shortcut_created": true
    },
    "cli_provider": {
      "enabled": true,
      "provider": "claude",
      "shortcut_created": true
    }
  },
  
  "cloud_apis": {
    "partner_node_linked": true,
    "third_party_keys": ["replicate"]
  }
}
```

### 10.2 Environment Report Schema

```python
@dataclass
class HardwareProfile:
    """
    Complete hardware detection result.
    See: docs/spec/HARDWARE_DETECTION.md for detection methods.
    """
  
    # Platform identification
    platform: str                    # "windows_nvidia", "apple_silicon", "linux_rocm"
    os_name: str                     # "Windows", "Darwin", "Linux"
    os_version: str
    arch: str                        # "x86_64", "arm64"
  
    # GPU
    gpu_vendor: str                  # "nvidia", "apple", "amd", "none"
    gpu_name: str                    # "NVIDIA GeForce RTX 4090"
    vram_gb: float                   # 24.0
    unified_memory: bool             # True for Apple Silicon
  
    # Compute capabilities
    compute_capability: Optional[float]  # 8.9 for RTX 4090
    supports_fp8: bool
    supports_bf16: bool
    supports_tf32: bool
    flash_attention_available: bool
    mps_available: bool              # For Apple Silicon
  
    # Memory
    ram_gb: float                    # 64.0
    memory_bandwidth_gbps: Optional[float]
  
    # Storage (see HARDWARE_DETECTION.md Section 4)
    disk_free_gb: float
    storage_type: str                # "nvme_gen4", "sata_ssd", "hdd"
    storage_tier: str                # "fast", "moderate", "slow"
    storage_read_mbps: int           # Estimated read speed
  
    # Multi-GPU
    gpu_count: int
    nvlink_available: bool
    
    # Form Factor (see HARDWARE_DETECTION.md Section 2)
    is_laptop: bool = False
    power_limit_watts: Optional[float] = None
    reference_tdp_watts: Optional[float] = None
    sustained_performance_ratio: float = 1.0
    
    # CPU (see HARDWARE_DETECTION.md Section 3)
    cpu_model: str = ""
    cpu_physical_cores: int = 0
    cpu_logical_cores: int = 0
    cpu_tier: str = "unknown"        # "high", "medium", "low", "minimal"
    supports_avx: bool = False
    supports_avx2: bool = False
    supports_avx512: bool = False
    
    # RAM Offload (see HARDWARE_DETECTION.md Section 5)
    ram_available_gb: float = 0      # Not used by OS/apps
    ram_for_offload_gb: float = 0    # Conservative estimate for AI use
  
    # Software
    python_version: str
    git_installed: bool
    comfyui_path: Optional[str]
    comfyui_version: Optional[str]
  
    # Derived
    hardware_tier: str               # "entry", "consumer", "prosumer", "professional", "workstation"
    warnings: List[str]
    
    # Helper methods
    def estimate_load_time(self, model_size_gb: float) -> float:
        """Estimate model load time in seconds."""
        return (model_size_gb * 1024) / self.storage_read_mbps
    
    def can_fit_model(self, size_gb: float, buffer_gb: float = 10) -> bool:
        """Check if storage can fit model with buffer."""
        return self.disk_free_gb >= (size_gb + buffer_gb)
```

@dataclass
class UserPreferences:
    """
    User preferences from onboarding, influences TOPSIS weights and warnings.
    """
    # Speed vs Quality tradeoff (0.0 = quality focused, 1.0 = speed focused)
    speed_priority: float = 0.5
    
    # Willingness to use cloud APIs
    cloud_willingness: str = "hybrid"  # "local_only", "hybrid", "cloud_preferred"
    
    # Budget constraints
    budget_conscious: bool = False
    
    # Technical comfort level
    technical_level: str = "intermediate"  # "beginner", "intermediate", "advanced"
```

### 10.3 Recommendation Output Schema

```python
@dataclass
class RecommendationResult:
    """Complete output of the recommendation engine."""
  
    recommendation_id: str
    timestamp: datetime
    confidence_score: float          # 0-1 overall confidence
  
    # Inputs (for reference)
    user_profile: UserProfile
    hardware_profile: HardwareProfile
  
    # Layer outputs
    constraint_rejections: List[RejectionReason]
    content_scores: Dict[str, float]  # model_id -> similarity
  
    # Final recommendations by category
    recommendations: Dict[str, List[RankedCandidate]]  # category -> ranked list
  
    # Installation manifest
    manifest: InstallationManifest
  
    # Explanations
    reasoning: List[str]
    warnings: List[str]


@dataclass
class RankedCandidate:
    """Single ranked recommendation."""
  
    model_id: str
    model_name: str
    rank: int
  
    # Scores
    topsis_score: float              # 0-1, closeness to ideal
    content_similarity: float        # 0-1
    hardware_fit: float              # 0-1
  
    # Selected variant
    selected_variant: ModelVariant
  
    # Resolution applied (if any)
    resolution: Optional[ResolutionResult]
  
    # Explanation
    matching_features: List[str]
    missing_features: List[str]
    explanation: str


@dataclass
class InstallationManifest:
    """Complete installation specification."""
  
    manifest_id: str
    created_at: datetime
  
    # Items to install
    custom_nodes: List[NodeInstall]
    models: List[ModelDownload]
    workflows: List[WorkflowInstall]
  
    # Totals
    total_size_gb: float
    estimated_time_minutes: int
  
    # Shortcuts to create
    shortcuts: List[ShortcutSpec]
```

---

## 11. Service Layer Specifications

### 11.1 Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Service Layer                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │ SetupWizard     │  │ Recommendation  │  │ Hardware        │         │
│  │ Service         │──│ Engine          │──│ Detector        │         │
│  │                 │  │ (3-Layer)       │  │ (Platform)      │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
│           │                   │                    │                    │
│           ▼                   ▼                    ▼                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │ Download        │  │ Model           │  │ Cloud Offload   │         │
│  │ Service         │  │ Manager         │  │ Strategy        │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
│           │                   │                    │                    │
│           ▼                   ▼                    ▼                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │ ComfyUI         │  │ Shortcut        │  │ Config          │         │
│  │ Service         │  │ Service         │  │ Manager         │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 11.2 SetupWizardService

```python
class SetupWizardService:
    """
    Orchestrates the full setup wizard flow.
    Coordinates between all other services.
    """
  
    def __init__(self):
        self.hardware_detector = HardwareDetector()
        self.recommendation_engine = RecommendationEngine()
        self.download_service = DownloadService()
        self.comfy_service = ComfyUIService()
        self.shortcut_service = ShortcutService()
        self.config_manager = ConfigManager()
  
        # State
        self.hardware_profile: Optional[HardwareProfile] = None
        self.user_profile: Optional[UserProfile] = None
        self.recommendations: Optional[RecommendationResult] = None
        self.installation_manifest: Optional[InstallationManifest] = None
  
    def start_wizard(self, path: str = "quick") -> None:
        """Initialize wizard with selected path."""
        self.wizard_path = path
        self.hardware_profile = None
        self.user_profile = None
        self.recommendations = None
  
    async def detect_hardware(self) -> HardwareProfile:
        """
        Run hardware detection.
        Automatically selects platform-specific detector.
        """
        self.hardware_profile = await self.hardware_detector.detect()
        return self.hardware_profile
  
    def process_onboarding_answers(
        self, 
        answers: Dict[str, Any]
    ) -> UserProfile:
        """
        Convert onboarding answers to UserProfile.
        Handles both quick and comprehensive paths.
        """
        if self.wizard_path == "quick":
            self.user_profile = self._build_quick_profile(answers)
        else:
            self.user_profile = self._build_comprehensive_profile(answers)
  
        return self.user_profile
  
    async def generate_recommendations(self) -> RecommendationResult:
        """
        Generate recommendations based on hardware and user profile.
        """
        if not self.hardware_profile or not self.user_profile:
            raise RuntimeError("Must detect hardware and complete onboarding first")
  
        self.recommendations = await self.recommendation_engine.recommend(
            user_profile=self.user_profile,
            hardware_profile=self.hardware_profile
        )
  
        return self.recommendations
  
    def customize_recommendations(
        self, 
        changes: Dict[str, Any]
    ) -> RecommendationResult:
        """
        Apply user customizations to recommendations.
        """
        # Re-run recommendation with modified inputs
        modified_profile = self._apply_customizations(
            self.user_profile, changes
        )
        return self.recommendation_engine.recommend(
            user_profile=modified_profile,
            hardware_profile=self.hardware_profile
        )
  
    async def execute_installation(
        self,
        manifest: InstallationManifest,
        progress_callback: Callable[[float, str], None]
    ) -> InstallationResult:
        """
        Execute the installation manifest.
        Reports progress via callback.
        """
        result = InstallationResult()
  
        # Phase 1: Dependencies
        progress_callback(0.0, "Checking dependencies...")
        await self._install_dependencies(manifest, result)
  
        # Phase 2: ComfyUI core
        progress_callback(0.1, "Installing ComfyUI...")
        await self.comfy_service.install_core(manifest.comfyui_path)
  
        # Phase 3: Custom nodes
        progress_callback(0.2, "Installing custom nodes...")
        for i, node in enumerate(manifest.custom_nodes):
            progress = 0.2 + (0.2 * i / len(manifest.custom_nodes))
            progress_callback(progress, f"Installing {node.name}...")
            await self.comfy_service.install_node(node)
  
        # Phase 4: Models (bulk of time)
        progress_callback(0.4, "Downloading models...")
        for i, model in enumerate(manifest.models):
            progress = 0.4 + (0.5 * i / len(manifest.models))
            progress_callback(progress, f"Downloading {model.name}...")
            try:
                await self.download_service.download(
                    url=model.url,
                    dest=model.dest_path,
                    expected_hash=model.hash_sha256,
                    progress_callback=lambda p: progress_callback(
                        progress + (0.5 / len(manifest.models)) * p,
                        f"Downloading {model.name}... {p:.0%}"
                    )
                )
                result.models_installed.append(model.model_id)
            except DownloadError as e:
                result.errors.append(f"Failed to download {model.name}: {e}")
  
        # Phase 5: Shortcuts
        progress_callback(0.95, "Creating shortcuts...")
        for shortcut in manifest.shortcuts:
            await self.shortcut_service.create(shortcut)
  
        # Phase 6: Validation
        progress_callback(0.98, "Validating installation...")
        result.validation = await self._validate_installation(manifest)
  
        # Complete
        progress_callback(1.0, "Installation complete!")
  
        # Update config
        await self.config_manager.update({
            "first_run": False,
            "wizard_completed": True,
            "wizard_version": "3.0"
        })
  
        return result
```

### 11.3 RecommendationEngine

```python
class RecommendationEngine:
    """
    Three-layer recommendation engine.
    Orchestrates CSP → Content-Based → TOPSIS pipeline.
    """
  
    def __init__(self, model_db: ModelDatabase):
        self.model_db = model_db
        self.constraint_layer = ConstraintSatisfactionLayer()
        self.content_layer = ContentBasedLayer()
        self.topsis_layer = TOPSISLayer()
        self.resolution_cascade = ResolutionCascade(model_db)
        self.explainer = RecommendationExplainer()
  
    async def recommend(
        self,
        user_profile: UserProfile,
        hardware_profile: HardwareProfile
    ) -> RecommendationResult:
        """
        Generate complete recommendations.
        """
        recommendations = {}
        all_rejections = []
        all_reasoning = []
  
        # Process each category the user needs
        for category in user_profile.use_cases:
            candidates = self.model_db.get_candidates_for_category(category)
      
            # Layer 1: Constraint Satisfaction
            viable, rejections = self.constraint_layer.filter_candidates(
                candidates=candidates,
                hardware=hardware_profile,
                user_constraints=user_profile.constraints
            )
            all_rejections.extend(rejections)
            all_reasoning.append(
                f"Layer 1: {len(viable)}/{len(candidates)} models viable for {category}"
            )
      
            # Layer 2: Content-Based Scoring
            scored = self.content_layer.score_candidates(
                candidates=viable,
                user_profile=user_profile
            )
      
            # Layer 3: TOPSIS Ranking
            ranked = self.topsis_layer.rank_candidates(
                scored_candidates=scored,
                hardware=hardware_profile
            )
      
            # Apply resolution cascade for top candidates
            for candidate in ranked[:3]:  # Top 3
                if candidate.candidate.requires_resolution:
                    resolution = self.resolution_cascade.resolve(
                        preferred_model=candidate.candidate,
                        hardware=hardware_profile,
                        user_constraints=user_profile.constraints
                    )
                    candidate.resolution = resolution
      
            recommendations[category] = ranked
  
        # Build installation manifest
        manifest = self._build_manifest(recommendations, hardware_profile)
  
        # Calculate confidence
        confidence = self._calculate_confidence(recommendations)
  
        return RecommendationResult(
            recommendation_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            confidence_score=confidence,
            user_profile=user_profile,
            hardware_profile=hardware_profile,
            constraint_rejections=all_rejections,
            content_scores={r.model_id: r.content_similarity 
                           for cat in recommendations.values() 
                           for r in cat},
            recommendations=recommendations,
            manifest=manifest,
            reasoning=all_reasoning,
            warnings=self._collect_warnings(recommendations)
        )
```

### 11.4 DownloadService

```python
class DownloadService:
    """
    Handle model downloads with retry, progress, and verification.
    """
  
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.max_retries = 3
        self.chunk_size = 1024 * 1024  # 1MB chunks
  
    async def download(
        self,
        url: str,
        dest: Path,
        expected_hash: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> None:
        """
        Download file with retry and progress reporting.
        """
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
  
        for attempt in range(self.max_retries):
            try:
                await self._download_with_progress(
                    url, dest, progress_callback
                )
          
                # Verify hash if provided
                if expected_hash:
                    actual_hash = await self._compute_hash(dest)
                    if actual_hash != expected_hash:
                        raise HashMismatchError(
                            f"Hash mismatch: expected {expected_hash}, got {actual_hash}"
                        )
          
                return  # Success
          
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    await asyncio.sleep(wait_time)
                else:
                    raise DownloadError(f"Failed after {self.max_retries} attempts: {e}")
  
    async def _download_with_progress(
        self,
        url: str,
        dest: Path,
        progress_callback: Optional[Callable[[float], None]]
    ) -> None:
        """Download with chunked progress reporting."""
        async with self.session.get(url) as response:
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
      
            with open(dest, 'wb') as f:
                async for chunk in response.content.iter_chunked(self.chunk_size):
                    f.write(chunk)
                    downloaded += len(chunk)
              
                    if progress_callback and total_size:
                        progress_callback(downloaded / total_size)
```

### 11.5 ShortcutService

```python
class ShortcutService:
    """
    Create desktop shortcuts across platforms.
    """
  
    async def create(self, spec: ShortcutSpec) -> None:
        """Create shortcut based on current platform."""
        if sys.platform == "win32":
            await self._create_windows_shortcut(spec)
        elif sys.platform == "darwin":
            await self._create_macos_shortcut(spec)
        else:
            await self._create_linux_shortcut(spec)
  
    async def _create_windows_shortcut(self, spec: ShortcutSpec) -> None:
        """Create .lnk shortcut on Windows."""
        import winshell
        from win32com.client import Dispatch
  
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(
            str(Path(spec.dest) / f"{spec.name}.lnk")
        )
        shortcut.Targetpath = spec.target
        shortcut.Arguments = spec.arguments
        shortcut.WorkingDirectory = spec.working_dir
        if spec.icon:
            shortcut.IconLocation = spec.icon
        shortcut.save()
  
    async def _create_macos_shortcut(self, spec: ShortcutSpec) -> None:
        """Create .command script on macOS."""
        script_path = Path(spec.dest) / f"{spec.name}.command"
  
        script_content = f"""#!/bin/bash
cd "{spec.working_dir}"
{spec.target} {spec.arguments}
"""
        script_path.write_text(script_content)
        os.chmod(script_path, 0o755)
  
    async def _create_linux_shortcut(self, spec: ShortcutSpec) -> None:
        """Create .desktop file on Linux."""
        desktop_path = Path(spec.dest) / f"{spec.name}.desktop"
  
        desktop_content = f"""[Desktop Entry]
Type=Application
Name={spec.name}
Exec={spec.target} {spec.arguments}
Path={spec.working_dir}
Terminal=true
"""
        if spec.icon:
            desktop_content += f"Icon={spec.icon}\n"
  
        desktop_path.write_text(desktop_content)
        os.chmod(desktop_path, 0o755)
```

---

## 12. UI Component Specifications

### 12.1 Component Architecture

```
src/ui/
├── wizard/
│   ├── setup_wizard.py           # Main wizard window
│   ├── path_selector.py          # Quick vs Comprehensive selection
│   ├── hardware_display.py       # Hardware detection results
│   └── components/
│       ├── question_card.py      # Single question display
│       ├── tier_progress.py      # Tiered question progress
│       ├── option_grid.py        # Multi-select grid
│       ├── slider_input.py       # Priority slider
│       ├── api_key_input.py      # API key entry
│       └── recommendation_preview.py  # Live recommendation preview
│
├── views/
│   ├── overview.py               # Dashboard overview
│   ├── comfyui.py                # ComfyUI management
│   ├── models.py                 # Model manager
│   ├── cloud_apis.py             # Cloud API configuration
│   └── settings.py               # Application settings
│
└── components/
    ├── model_card.py             # Model display card
    ├── download_progress.py      # Download progress indicator
    ├── reasoning_display.py      # Recommendation reasoning
    ├── hardware_badge.py         # Hardware tier badge
    └── warning_banner.py         # Warning/info banners
```

### 12.2 Setup Wizard Components

#### 12.2.1 Path Selector

```python
class PathSelectorView(QWidget):
    """
    Initial path selection: Quick Setup vs Comprehensive Setup.
    """
  
    path_selected = Signal(str)  # "quick" or "comprehensive"
  
    def __init__(self):
        super().__init__()
        self._setup_ui()
  
    def _setup_ui(self):
        layout = QVBoxLayout(self)
  
        # Header
        header = QLabel("How would you like to set up your AI workstation?")
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(header)
  
        # Path cards
        cards_layout = QHBoxLayout()
  
        # Quick Setup card
        quick_card = PathCard(
            title="🚀 Quick Setup",
            subtitle="~2 minutes",
            features=[
                "5 questions",
                "Smart defaults",
                "Easy to adjust later"
            ],
            description="Best for exploring or getting started",
            path="quick"
        )
        quick_card.clicked.connect(lambda: self.path_selected.emit("quick"))
        cards_layout.addWidget(quick_card)
  
        # Comprehensive card
        comp_card = PathCard(
            title="🎯 Comprehensive Setup",
            subtitle="~5-8 minutes",
            features=[
                "15-20 questions",
                "Precise recommendations",
                "Optimized for your needs"
            ],
            description="Best if you know what you want to create",
            path="comprehensive"
        )
        comp_card.clicked.connect(lambda: self.path_selected.emit("comprehensive"))
        cards_layout.addWidget(comp_card)
  
        layout.addLayout(cards_layout)
```

#### 12.2.2 Tiered Question Flow

```python
class TieredQuestionFlow(QWidget):
    """
    Progressive question flow for comprehensive setup.
    Shows one tier at a time with progress indicator.
    """
  
    completed = Signal(dict)  # All answers
  
    def __init__(self, tiers: List[QuestionTier]):
        super().__init__()
        self.tiers = tiers
        self.current_tier_index = 0
        self.answers = {}
        self._setup_ui()
  
    def _setup_ui(self):
        layout = QVBoxLayout(self)
  
        # Progress indicator
        self.progress = TierProgressIndicator(self.tiers)
        layout.addWidget(self.progress)
  
        # Question area (stacked widget for tiers)
        self.tier_stack = QStackedWidget()
        for tier in self.tiers:
            tier_widget = TierQuestionWidget(tier)
            tier_widget.completed.connect(self._on_tier_completed)
            self.tier_stack.addWidget(tier_widget)
        layout.addWidget(self.tier_stack)
  
        # Live recommendation preview (sidebar)
        self.preview = RecommendationPreview()
        # ... sidebar layout
  
    def _on_tier_completed(self, tier_answers: dict):
        """Handle tier completion, show next or finish."""
        self.answers.update(tier_answers)
  
        # Find next applicable tier
        next_tier = self._find_next_tier()
        if next_tier:
            self.current_tier_index = self.tiers.index(next_tier)
            self.tier_stack.setCurrentIndex(self.current_tier_index)
            self.progress.set_current(self.current_tier_index)
        else:
            self.completed.emit(self.answers)
  
    def _find_next_tier(self) -> Optional[QuestionTier]:
        """Find next tier that should be shown based on answers."""
        for tier in self.tiers[self.current_tier_index + 1:]:
            if tier.should_show(self.answers):
                return tier
        return None
```

#### 12.2.3 Recommendation Preview

```python
class RecommendationPreview(QWidget):
    """
    Live preview of recommendations that updates as user answers questions.
    """
  
    def __init__(self):
        super().__init__()
        self.recommendation_engine = RecommendationEngine()
        self._setup_ui()
  
    def _setup_ui(self):
        layout = QVBoxLayout(self)
  
        header = QLabel("Your Setup Preview")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)
  
        # Model list
        self.model_list = QListWidget()
        layout.addWidget(self.model_list)
  
        # Totals
        self.size_label = QLabel("Total size: --")
        self.time_label = QLabel("Est. install time: --")
        layout.addWidget(self.size_label)
        layout.addWidget(self.time_label)
  
    def update_preview(
        self, 
        partial_answers: dict, 
        hardware: HardwareProfile
    ):
        """Update preview based on current answers."""
        # Generate preliminary recommendations
        preliminary = self.recommendation_engine.preliminary_recommend(
            partial_answers, hardware
        )
  
        # Update UI
        self.model_list.clear()
        for model in preliminary.models[:5]:  # Top 5
            item = QListWidgetItem(f"{model.name} ({model.size_gb:.1f}GB)")
            self.model_list.addItem(item)
  
        self.size_label.setText(
            f"Total size: ~{preliminary.total_size_gb:.1f}GB"
        )
        self.time_label.setText(
            f"Est. install time: ~{preliminary.estimated_time_minutes} min"
        )
```

### 12.3 Model Manager Components

#### 12.3.1 Model Card

```python
class ModelCard(QFrame):
    """
    Display card for a single model.
    Shows status, size, actions.
    """
  
    install_clicked = Signal(str)  # model_id
    delete_clicked = Signal(str)
  
    def __init__(self, model: ModelInfo, installed: bool = False):
        super().__init__()
        self.model = model
        self.installed = installed
        self._setup_ui()
  
    def _setup_ui(self):
        self.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(self)
  
        # Header row
        header = QHBoxLayout()
  
        name = QLabel(self.model.name)
        name.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(name)
  
        # Hardware fit badge
        if self.model.fits_hardware:
            badge = HardwareBadge("✅ Fits", "green")
        else:
            badge = HardwareBadge("⚠️ May be slow", "orange")
        header.addWidget(badge)
  
        layout.addLayout(header)
  
        # Details
        details = QLabel(
            f"{self.model.category} • {self.model.size_gb:.1f}GB"
        )
        details.setStyleSheet("color: gray;")
        layout.addWidget(details)
  
        # Explanation
        if self.model.explanation:
            explanation = QLabel(self.model.explanation)
            explanation.setWordWrap(True)
            explanation.setStyleSheet("font-style: italic;")
            layout.addWidget(explanation)
  
        # Actions
        actions = QHBoxLayout()
        if self.installed:
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(
                lambda: self.delete_clicked.emit(self.model.id)
            )
            actions.addWidget(delete_btn)
        else:
            install_btn = QPushButton("Install")
            install_btn.clicked.connect(
                lambda: self.install_clicked.emit(self.model.id)
            )
            actions.addWidget(install_btn)
  
        layout.addLayout(actions)
```

#### 12.3.2 Reasoning Display

```python
class ReasoningDisplay(QWidget):
    """
    Expandable display of recommendation reasoning.
    Shows why a model was recommended or rejected.
    """
  
    def __init__(self, recommendation: RankedCandidate):
        super().__init__()
        self.recommendation = recommendation
        self._setup_ui()
  
    def _setup_ui(self):
        layout = QVBoxLayout(self)
  
        # Summary (always visible)
        summary = QLabel(self.recommendation.explanation)
        summary.setWordWrap(True)
        layout.addWidget(summary)
  
        # Expandable details
        details_btn = QPushButton("Show details ▼")
        details_btn.setFlat(True)
        layout.addWidget(details_btn)
  
        self.details_widget = QWidget()
        self.details_widget.hide()
        details_layout = QVBoxLayout(self.details_widget)
  
        # Scores
        scores_header = QLabel("Scores:")
        scores_header.setStyleSheet("font-weight: bold;")
        details_layout.addWidget(scores_header)
  
        score_text = f"""
        • Overall match: {self.recommendation.topsis_score:.0%}
        • Feature similarity: {self.recommendation.content_similarity:.0%}
        • Hardware fit: {self.recommendation.hardware_fit:.0%}
        """
        details_layout.addWidget(QLabel(score_text))
  
        # Matching features
        if self.recommendation.matching_features:
            match_header = QLabel("Matching features:")
            match_header.setStyleSheet("font-weight: bold;")
            details_layout.addWidget(match_header)
      
            for feature in self.recommendation.matching_features:
                details_layout.addWidget(QLabel(f"  ✓ {feature}"))
  
        # Missing features
        if self.recommendation.missing_features:
            missing_header = QLabel("Not included:")
            missing_header.setStyleSheet("font-weight: bold;")
            details_layout.addWidget(missing_header)
      
            for feature in self.recommendation.missing_features:
                details_layout.addWidget(QLabel(f"  ✗ {feature}"))
  
        layout.addWidget(self.details_widget)
  
        # Toggle behavior
        details_btn.clicked.connect(self._toggle_details)
  
    def _toggle_details(self):
        visible = not self.details_widget.isVisible()
        self.details_widget.setVisible(visible)
        sender = self.sender()
        sender.setText("Hide details ▲" if visible else "Show details ▼")
```

---

## 13. File Structure

### 13.1 Complete Project Structure

```
ai-universal-suite/
├── src/
│   ├── __init__.py
│   ├── main.py                      # Application entry point
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── setup_wizard_service.py  # Wizard orchestration
│   │   ├── recommendation_engine.py # 3-layer recommendation
│   │   ├── constraint_layer.py      # Layer 1: CSP
│   │   ├── content_layer.py         # Layer 2: Content-based
│   │   ├── topsis_layer.py          # Layer 3: TOPSIS
│   │   ├── resolution_cascade.py    # Hardware resolution
│   │   ├── hardware_detector.py     # Platform-specific detection
│   │   ├── download_service.py      # Download with retry/progress
│   │   ├── model_manager_service.py # Model management
│   │   ├── cloud_offload_service.py # Cloud API strategy
│   │   ├── comfy_service.py         # ComfyUI management
│   │   ├── shortcut_service.py      # Desktop shortcuts
│   │   └── config_manager.py        # Configuration persistence
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py           # Main application window
│   │   │
│   │   ├── wizard/
│   │   │   ├── __init__.py
│   │   │   ├── setup_wizard.py      # Main wizard window
│   │   │   ├── path_selector.py     # Quick/Comprehensive selection
│   │   │   ├── hardware_display.py  # Hardware confirmation
│   │   │   ├── tiered_flow.py       # Tiered question flow
│   │   │   └── components/
│   │   │       ├── question_card.py
│   │   │       ├── option_grid.py
│   │   │       ├── slider_input.py
│   │   │       ├── api_key_input.py
│   │   │       └── recommendation_preview.py
│   │   │
│   │   ├── views/
│   │   │   ├── __init__.py
│   │   │   ├── overview.py          # Dashboard overview
│   │   │   ├── comfyui.py           # ComfyUI management
│   │   │   ├── models.py            # Model manager
│   │   │   ├── cloud_apis.py        # Cloud API config
│   │   │   └── settings.py          # Application settings
│   │   │
│   │   └── components/
│   │       ├── __init__.py
│   │       ├── model_card.py
│   │       ├── download_progress.py
│   │       ├── reasoning_display.py
│   │       ├── hardware_badge.py
│   │       └── warning_banner.py
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── defaults.py              # Default configuration
│   │   └── schema.py                # Configuration schemas
│   │
│   └── utils/
│       ├── __init__.py
│       ├── async_utils.py
│       ├── hash_utils.py
│       └── platform_utils.py
│
├── data/
│   ├── models.yaml                  # Model database (external ref)
│   ├── onboarding_questions.yaml    # Question definitions
│   └── workflows/                   # Bundled workflow templates
│       ├── wan_i2v_basic.json
│       ├── flux_t2i_basic.json
│       └── previews/
│           ├── wan_i2v_basic.png
│           └── flux_t2i_basic.png
│
├── tests/
│   ├── __init__.py
│   ├── test_constraint_layer.py
│   ├── test_content_layer.py
│   ├── test_topsis_layer.py
│   ├── test_recommendation_engine.py
│   ├── test_hardware_detection.py
│   └── test_integration.py
│
├── docs/
│   ├── SPEC_v3.md                   # This document
│   └── models_database.yaml         # Complete model reference
│
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 14. Implementation Phases

### 14.1 Phase Overview

| Phase   | Focus                 | Duration | Priority |
| ------- | --------------------- | -------- | -------- |
| Phase 1 | Core Infrastructure   | 2 weeks  | CRITICAL |
| Phase 2 | Onboarding System     | 2 weeks  | HIGH     |
| Phase 3 | Recommendation Engine | 2 weeks  | HIGH     |
| Phase 4 | Model Management      | 1 week   | HIGH     |
| Phase 5 | Cloud Integration     | 1 week   | MEDIUM   |
| Phase 6 | Polish & Testing      | 2 weeks  | MEDIUM   |

### 14.2 Phase 1: Core Infrastructure (Weeks 1-2)

**Objective**: Establish foundation services and fix critical issues.

#### Week 1: Platform Detection

- [ ] Implement `HardwareDetector` base class
- [ ] Implement `AppleSiliconDetector` with sysctl calls
- [ ] Implement `NVIDIADetector` with CUDA capability detection
- [ ] Implement `AMDROCmDetector` with ROCm detection
- [ ] Add storage type detection (NVMe/SATA/HDD)
- [ ] Create `HardwareProfile` dataclass with all fields
- [ ] Add hardware tier classification logic

**Critical Fix**: Apple Silicon RAM detection (currently hardcoded to 16GB)

#### Week 2: Configuration & Services

- [ ] Implement `ConfigManager` with v3.0 schema
- [ ] Implement `DownloadService` with retry and progress
- [ ] Implement `ShortcutService` for all platforms
- [ ] Create base `SetupWizardService` skeleton
- [ ] Add logging infrastructure
- [ ] Write unit tests for hardware detection

### 14.3 Phase 2: Onboarding System (Weeks 3-4)

**Objective**: Implement dual-path onboarding flow.

#### Week 3: Question System

- [ ] Define question schemas in YAML
- [ ] Implement `QuestionCard` component
- [ ] Implement `OptionGrid` for multi-select
- [ ] Implement `SliderInput` for priority slider
- [ ] Implement `PathSelectorView`
- [ ] Implement `HardwareDisplayView`

#### Week 4: Tiered Flow

- [ ] Implement `TieredQuestionFlow` widget
- [ ] Implement tier visibility logic (show_if conditions)
- [ ] Implement `RecommendationPreview` sidebar
- [ ] Implement `APIKeyInput` with provider selection
- [ ] Connect onboarding to `UserProfile` generation
- [ ] Write integration tests for full flows

### 14.4 Phase 3: Recommendation Engine (Weeks 5-6)

**Objective**: Implement three-layer recommendation architecture.

#### Week 5: Layers 1 & 2

- [ ] Implement `ConstraintSatisfactionLayer`
  - [ ] VRAM constraint with quantization fallback
  - [ ] Platform compatibility checks
  - [ ] Compute capability requirements
  - [ ] Storage constraints
- [ ] Implement `ContentBasedLayer`
  - [ ] User feature vector construction
  - [ ] Model capability vector construction
  - [ ] Cosine similarity calculation
  - [ ] Feature matching identification

#### Week 6: Layer 3 & Resolution

- [ ] Implement `TOPSISLayer`
  - [ ] Decision matrix construction
  - [ ] Vector normalization
  - [ ] Ideal/anti-ideal solution calculation
  - [ ] Closeness coefficient computation
- [ ] Implement `ResolutionCascade`
  - [ ] Quantization downgrade path
  - [ ] Variant substitution logic
  - [ ] Cloud offload suggestion
- [ ] Implement `RecommendationExplainer`
- [ ] Write comprehensive recommendation tests

### 14.5 Phase 4: Model Management (Week 7)

**Objective**: Implement model download and management.

- [ ] Create `models.yaml` database with full schema
- [ ] Implement `ModelDatabase` with querying
- [ ] Implement `ModelManagerService`
- [ ] Implement `ModelCard` component
- [ ] Implement download queue with progress
- [ ] Implement model deletion
- [ ] Add model update checking
- [ ] Write model management tests

### 14.6 Phase 5: Cloud Integration (Week 8)

**Objective**: Implement Partner Node and API key management.

- [ ] Implement `PartnerNodeManager`
  - [ ] Account status checking
  - [ ] Service availability listing
- [ ] Implement `ThirdPartyAPIManager`
  - [ ] Key storage in ComfyUI/keys/
  - [ ] Provider configuration
- [ ] Implement `CloudOffloadStrategy`
- [ ] Implement `CloudAPIsView`
- [ ] Add cost estimation display
- [ ] Write cloud integration tests

### 14.7 Phase 6: Polish & Testing (Weeks 9-10)

**Objective**: Complete integration, testing, and polish.

#### Week 9: Integration

- [ ] Full wizard flow integration testing
- [ ] Cross-platform testing (Windows, Mac, Linux)
- [ ] Error handling and recovery
- [ ] Performance optimization
- [ ] UI polish and consistency

#### Week 10: Documentation & Release

- [ ] Update all documentation
- [ ] Create user guide
- [ ] Create troubleshooting guide
- [ ] Package for distribution
- [ ] Beta testing
- [ ] Release preparation

---

## 15. Testing Requirements

### 15.1 Unit Tests

```python
# tests/test_constraint_layer.py

def test_vram_constraint_rejects_oversized_model():
    """Verify constraint layer rejects models exceeding VRAM."""
    hardware = HardwareProfile(vram_gb=8, unified_memory=False)
    model = ModelCandidate(min_vram_gb=24, variants=[])
  
    layer = ConstraintSatisfactionLayer()
    viable, rejections = layer.filter_candidates([model], hardware)
  
    assert len(viable) == 0
    assert len(rejections) == 1
    assert rejections[0].constraint == "vram"

def test_vram_constraint_accepts_quantized_variant():
    """Verify quantized variant passes when FP16 fails."""
    hardware = HardwareProfile(vram_gb=8, unified_memory=False)
    model = ModelCandidate(
        min_vram_gb=24,
        variants=[
            ModelVariant(precision="fp16", vram_min_mb=24000),
            ModelVariant(precision="gguf_q4", vram_min_mb=6000)
        ]
    )
  
    layer = ConstraintSatisfactionLayer()
    viable, _ = layer.filter_candidates([model], hardware)
  
    assert len(viable) == 1

def test_apple_silicon_rejects_fp8_only():
    """Verify FP8-only models rejected on Apple Silicon."""
    hardware = HardwareProfile(
        platform="apple_silicon",
        supports_fp8=False,
        vram_gb=24
    )
    model = ModelCandidate(
        requires_fp8=True,
        variants=[ModelVariant(precision="fp8", vram_min_mb=12000)]
    )
  
    layer = ConstraintSatisfactionLayer()
    _, rejections = layer.filter_candidates([model], hardware)
  
    assert len(rejections) == 1
    assert "FP8" in rejections[0].message
```

### 15.2 Integration Tests

```python
# tests/test_recommendation_flow.py

async def test_quick_setup_produces_valid_manifest():
    """Full quick setup flow produces installable manifest."""
    wizard = SetupWizardService()
  
    # Simulate hardware detection
    hardware = await wizard.detect_hardware()
  
    # Simulate quick setup answers
    answers = {
        "use_cases": ["images"],
        "experience_level": "regular",
        "priority_slider": 0.5,
        "cloud_willingness": "cloud_fallback"
    }
    wizard.process_onboarding_answers(answers)
  
    # Generate recommendations
    result = await wizard.generate_recommendations()
  
    # Verify manifest is valid
    assert result.manifest is not None
    assert len(result.manifest.models) > 0
    assert result.manifest.total_size_gb > 0

async def test_comprehensive_video_setup_includes_wan():
    """Comprehensive video setup includes Wan models."""
    wizard = SetupWizardService()
  
    hardware = HardwareProfile(vram_gb=12, platform="windows_nvidia")
    wizard.hardware_profile = hardware
  
    answers = {
        "use_cases": ["video"],
        "experience_level": "regular",
        "priority_slider": 0.6,
        "video_modes": ["i2v", "flf2v"],
        "duration": "short"
    }
    wizard.process_onboarding_answers(answers)
  
    result = await wizard.generate_recommendations()
  
    model_ids = [m.model_id for m in result.manifest.models]
    assert any("wan" in m.lower() for m in model_ids)
```

### 15.3 Platform-Specific Tests

```python
# tests/test_platform_specific.py

@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
def test_apple_silicon_detection():
    """Verify Apple Silicon detection on macOS."""
    detector = AppleSiliconDetector()
    profile = detector.detect()
  
    assert profile.platform == "apple_silicon"
    assert profile.unified_memory == True
    assert profile.supports_fp8 == False
    assert profile.vram_gb > 0

@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
def test_nvidia_compute_capability():
    """Verify compute capability detection on NVIDIA."""
    detector = NVIDIADetector()
    profile = detector.detect()
  
    assert profile.compute_capability is not None
    assert profile.compute_capability >= 7.0
    assert profile.supports_bf16 == (profile.compute_capability >= 8.0)
```

### 15.4 Success Metrics

| Metric                         | Target | Measurement                                |
| ------------------------------ | ------ | ------------------------------------------ |
| Quick setup completion         | >95%   | Users who start finish                     |
| Comprehensive setup completion | >85%   | Users who start finish                     |
| Recommendation acceptance      | >80%   | Users don't immediately customize          |
| Installation success           | >90%   | Installations complete without error       |
| First generation success       | >95%   | Users can generate within 5 min of install |
| Question abandonment           | <5%    | Per-question drop-off rate                 |

---

## Appendix A: Migration from v2.0

For users of v2.0 specification:

1. **Configuration Migration**

   - v2.0 `config.json` → v3.0 schema
   - Add new fields with defaults
   - Preserve user preferences
2. **Recommendation Algorithm**

   - v2.0 weighted scoring → v3.0 three-layer architecture
   - Internal dimensions remain valid
   - Only user-facing collection changes
3. **Model Database**

   - v2.0 inline models → v3.0 external `models.yaml`
   - Expand variant coverage
   - Add cloud availability fields

---

## Appendix B: Research Citations

| Finding                          | Source                    | Application                  |
| -------------------------------- | ------------------------- | ---------------------------- |
| 5-7 question threshold           | InMoment survey research  | Quick Setup path             |
| 4±1 evaluable constructs        | Cowan 2001 cognitive load | 5 aggregated factors         |
| Presets + override pattern       | Game settings research    | Dual path with customization |
| TOPSIS for ranking               | MCDA literature           | Layer 3 architecture         |
| Content-based over collaborative | Technical domain research | Layer 2 architecture         |

---

*End of Specification v3.0*

*Last Updated: January 2026*
*Consolidates: AI_UNIVERSAL_SUITE_SPECS.md v2.0, SPEC_ADDENDUM_v2_1.md, SPEC_ADDENDUM_HARDWARE_AND_MODELS_v1.md, AI_Universal_Suite_Research_Addendum_v2.md, Complete_Guide_to_AI_Generation_Models_in_ComfyUI.md*
