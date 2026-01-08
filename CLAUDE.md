# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate virtual environment
# Windows:
.dashboard_env\venv\Scripts\activate
# macOS/Linux:
source .dashboard_env/venv/bin/activate

# Run the application
python src/main.py

# First-time setup (auto-creates venv, installs deps, launches)
python launch.py
```

## Source of Truth

- **Specification**: `docs/spec/AI_UNIVERSAL_SUITE_SPEC_v3.md` - Architecture, algorithms, schemas
- **Hardware Detection**: `docs/spec/HARDWARE_DETECTION.md` - GPU, CPU, Storage, RAM detection
- **CUDA/PyTorch**: `docs/spec/CUDA_PYTORCH_INSTALLATION.md` - PyTorch installation logic
- **Architecture Principles**: `docs/ARCHITECTURE_PRINCIPLES.md` - Coding patterns, anti-patterns
- **Migration Protocol**: `docs/MIGRATION_PROTOCOL.md` - TDD workflow, safe refactoring
- **Task Tracker**: `docs/plan/PLAN_v3.md` - Current phase, decisions, gaps
- **Model Database**: `data/models_database.yaml` - 100+ model definitions

**If code contradicts the spec, the spec is correct.**
**If code violates architecture principles, the code is wrong.**

## Project Overview

**AI Universal Suite** is a cross-platform desktop app that configures AI workstations through a guided wizard.

Core principle: **Zero terminal interaction** - every action achievable through GUI.

This includes:
- **PyTorch/CUDA installation** - auto-detected GPU, auto-installed correct version
- **Model downloads** - handled by DownloadService with progress UI
- **ComfyUI setup** - cloned and configured automatically
- **Custom node installation** - via ComfyUI-Manager integration

**Users should NEVER need to run pip, git, or any terminal commands.**

Tech stack: Python 3.10+, CustomTkinter, Service-Oriented Architecture

## Current Gaps (Code vs Spec)

| Area | Current Code | Spec Requires | Files to Fix |
|------|--------------|---------------|--------------|
| Recommendation | Single-pass weighted scoring | 3-layer: CSP→Content→TOPSIS | `scoring_service.py` (stubs ready in `recommendation/`) |
| ~~PyTorch Install~~ | ~~Detection only~~ | ~~Auto-install correct CUDA/PyTorch~~ | ✅ FIXED: `pytorch_service.py` |
| Onboarding | Single use-case-first path | Dual-path (Quick 5 / Comprehensive 15-20) | `setup_wizard.py` |
| ~~Model Source~~ | ~~Reads `resources.json`~~ | ~~Use `models_database.yaml`~~ | ✅ FIXED: `model_database.py` |
| ~~Hardware Detection~~ | ~~16GB fallback~~ | ~~Platform-specific detectors~~ | ✅ FIXED: `services/hardware/` |
| ~~Platform Constraints~~ | ~~Not enforced~~ | ~~K-quant filtering, memory ceiling~~ | ✅ FIXED: `hardware.py` |

## Architecture

### Three-Layer Recommendation Engine (SPEC Section 6)

```
Layer 1: CSP (Constraint Satisfaction)
    → Binary elimination: VRAM, platform, compute capability
    → File: constraint_layer.py ✅ (stub exists, Phase 3 implementation)

Layer 2: Content-Based Filtering (Modular Modality Architecture)
    → Modality-specific scorers (ImageScorer, VideoScorer, etc.)
    → Cosine similarity per modality, not flat vector
    → UseCaseDefinition composes required modalities
    → File: content_layer.py ✅ (stub exists, Phase 3 implementation)

Layer 3: TOPSIS Multi-Criteria Ranking
    → 5 criteria: content_similarity, hardware_fit, speed_fit, ecosystem_maturity, approach_fit
    → Closeness coefficients with explainable scores
    → File: topsis_layer.py ✅ (stub exists, Phase 3 implementation)

Resolution Cascade: quantization → cpu_offload → substitution → workflow → cloud
```

### Hardware → Recommendation Integration

| Hardware Element | Layer 1 | Layer 3 | Resolution | Warnings |
|------------------|---------|---------|------------|----------|
| VRAM | `_check_vram_constraint` | `hardware_fit` | Quantization | - |
| CPU Tier | `_can_offload_to_cpu` | - | `_try_cpu_offload` | Offload active |
| CPU AVX2 | GGUF offload check | - | - | Performance warning |
| Storage Space | `_check_storage_constraint` | - | `adjust_for_space` | - |
| Storage Speed | - | `speed_fit` | - | Speed warning |
| Form Factor | - | `hardware_fit` penalty | - | Laptop warning |
| RAM for Offload | Offload viability | - | CPU offload | Low RAM warning |
| Memory Bandwidth | - | LLM tok/s estimate | - | - |

### File Structure

```
src/
├── config/
│   ├── manager.py              # Config read/write
│   └── resources.json          # Legacy - migrate to models_database.yaml
├── schemas/
│   ├── environment.py          # EnvironmentReport dataclass
│   ├── hardware.py             # HardwareProfile, CPUProfile, RAMProfile, etc.
│   ├── recommendation.py       # UserProfile, candidates, results
│   └── installation.py         # InstallationManifest, items
├── services/
│   ├── hardware/               # NEW: Platform-specific hardware detection
│   │   ├── base.py             # HardwareDetector ABC, exceptions
│   │   ├── nvidia.py           # NVIDIA GPU detection
│   │   ├── apple_silicon.py    # Apple Silicon detection
│   │   ├── amd_rocm.py         # AMD ROCm detection
│   │   ├── cpu.py              # CPU detection (cross-platform)
│   │   ├── ram.py              # RAM detection and offload calculation
│   │   ├── storage.py          # Storage type detection
│   │   └── form_factor.py      # Desktop/laptop detection
│   ├── system_service.py       # Legacy hardware detection (HAS BUGS)
│   ├── scoring_service.py      # Old architecture (REPLACE)
│   ├── recommendation_service.py # Orchestrator (REFACTOR)
│   ├── comfy_service.py        # ComfyUI integration
│   ├── download_service.py     # File downloads (STUB)
│   └── shortcut_service.py     # Desktop shortcuts (STUB)
├── ui/
│   ├── app.py                  # Main window (CustomTkinter)
│   ├── wizard/
│   │   ├── setup_wizard.py     # Wizard flow (WRONG FLOW)
│   │   └── components/         # UI components (KEEP)
│   ├── views/                  # Module dashboards
│   └── components/             # Reusable UI components
└── utils/
    ├── logger.py
    └── subprocess_utils.py     # NEW: I/O normalization utilities
```

## Platform Constraints (HARDWARE_DETECTION.md)

### Apple Silicon (40% of users)
- GGUF K-quants crash MPS: **Filter to Q4_0, Q5_0, Q8_0 only**
- Memory ceiling: **75% of unified memory** for effective VRAM
- **Exclude HunyuanVideo** (~16 min/clip) - use AnimateDiff instead

### NVIDIA - Blackwell (RTX 50 series)
- Compute capability: **sm_120** (12.0)
- Requires: **CUDA 12.8+** or **CUDA 13.x** (preferred)
- PyTorch: `cu128` or `cu130` builds
- Supports: FP4, FP6, FP8 (2nd gen), BF16

### NVIDIA - Form Factor Detection
- Mobile GPUs have lower sustained performance than desktop
- Detect power limit via `nvidia-smi --query-gpu=power.limit`
- Performance ratio = sqrt(actual_power / reference_tdp)
- Example: RTX 4090 Laptop (175W) = ~62% of RTX 4090 Desktop (450W)

### NVIDIA - Ada Lovelace (RTX 40 series)
- Compute capability: **sm_89** (8.9)
- FP8 requires compute capability 8.9+

### NVIDIA - Older (RTX 30/20 series)
- Ampere (sm_80/86): BF16, no FP8
- Turing (sm_75): FP16 Tensor Cores only

### AMD ROCm (20% of users)
- Mark as **experimental** in UI
- RDNA2 may need `HSA_OVERRIDE_GFX_VERSION`

### CPU Detection
- Detect cores, model, AVX support
- Tiers: HIGH (16+), MEDIUM (8-15), LOW (4-7), MINIMAL (<4)
- Affects GGUF viability and offload capacity

### Storage Detection
- Types: NVMe Gen3/4/5, SATA SSD, HDD
- Tiers: FAST (NVMe), MODERATE (SATA), SLOW (HDD)
- Affects model load times and space constraints

## Development Conventions

1. **Strict Separation**: UI files must NEVER contain business logic
2. **Type Hints**: Required on all function signatures
3. **Schemas not Models**: Use `src/schemas/` for dataclasses
4. **Spec Citations**: Reference in commits: `fix(hardware): Apple Silicon RAM per SPEC_v3 4.2`
5. **Model Data**: Use `data/models_database.yaml`, NOT `resources.json`
6. **Migration Protocol**: See `docs/MIGRATION_PROTOCOL.md` - don't break working app during refactor
7. **Commit Messages**: Never add co-author tags, AI tool attribution, or "Generated with" footers to commit messages unless explicitly requested by the user

### Architecture Principles (see `docs/ARCHITECTURE_PRINCIPLES.md`)

- **I/O Normalization**: All shell output parsed with `src/utils/subprocess_utils.py` utilities
- **No Magic Numbers**: All calculations use formulas or documented constants
- **Lookup Tables**: Hardware specs from published sources with encapsulated lookups
- **Nested Profiles**: Hardware data uses dataclasses with tier classification
- **Explicit Failure**: Detection failures raise errors, not silent defaults

## Locked Decisions (Do Not Relitigate)

Key decisions are final. For full rationale, see `docs/plan/PLAN_v3.md` Section 1 Decision Log.

| Area | Decision |
|------|----------|
| Recommendation | 3-layer (CSP→Content→TOPSIS) |
| Content Layer | Modular modality architecture (per-modality scorers) |
| Onboarding | Dual-path (Quick 5 / Comprehensive 15-20) |
| HardwareTier | Effective capacity (VRAM + offload), not VRAM-only |
| Model database | `data/models_database.yaml` |
| Cloud APIs | Partner Nodes primary (ComfyUI 0.3.60+) |
| Platform split | 40% Mac, 40% Windows, 20% Linux |

## Decision Workflow for Architecture Changes

**Before implementing any architecture/spec change**, follow this workflow:

1. **Document Decision** → Add to `PLAN_v3.md` Section 1 (Decision Log)
2. **Document Deprecations** → Add to `PLAN_v3.md` Section 7 (Deprecation Tracker)
3. **Update Spec** → Modify `AI_UNIVERSAL_SUITE_SPEC_v3.md`
4. **Update Plan** → Add tasks to `PLAN_v3.md` Section 2 (Task Tracker)
5. **Update Agent Files** → `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`
6. **Implement** → Follow Migration Protocol

This ensures all documentation stays in sync with code changes.

## Current Phase

**Phase 1: Core Infrastructure** - IN PROGRESS

Completed:
- ~~Audit codebase against spec~~ ✅
- ~~Week 1: Hardware detection infrastructure~~ ✅
  - `HardwareProfile` dataclass with nested profiles (CPU, RAM, Storage, FormFactor)
  - Platform-specific detectors (NVIDIA, Apple Silicon, AMD ROCm)
  - Shared utilities (`src/utils/subprocess_utils.py`)
  - Architecture principles documented
- ~~Week 2a: Extended detection (CPU, RAM, Storage, FormFactor)~~ ✅

In progress:
- Week 2b: Integration testing with real hardware
- Migrate model loading to `models_database.yaml`
- Stub out 3-layer recommendation classes

See `docs/plan/PLAN_v3.md` Section 2 for full task list.
