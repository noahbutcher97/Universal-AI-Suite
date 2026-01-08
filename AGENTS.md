# AI Universal Suite - Agent Context

> **For Claude Code**: Use `CLAUDE.md` instead (auto-loaded with full context)

## Source of Truth

**The specification defines how this project should work. Your job is to align the codebase with it.**

Read these files in order:
1. `docs/spec/AI_UNIVERSAL_SUITE_SPEC_v3.md` - Complete technical specification
2. `docs/spec/HARDWARE_DETECTION.md` - GPU, CPU, Storage, RAM detection methods
3. `docs/spec/CUDA_PYTORCH_INSTALLATION.md` - PyTorch/CUDA installation logic
4. `docs/plan/PLAN_v3.md` - Decision log, task tracker, current phase (see Section 0 for gaps)
5. `data/models_database.yaml` - Model definitions with variants and hardware requirements

If code contradicts the spec, the spec is correct (unless the spec has an obvious error, in which case flag it).

---

## Project Identity

**AI Universal Suite** is a cross-platform desktop application that configures AI workstations through a guided wizard. It detects hardware, asks about user needs, and recommends optimal configurations of models, tools, and workflows.

**Core Principle:** Zero terminal interaction - every action achievable through GUI.

**Current Phase:** See `docs/plan/PLAN_v3.md` for current status

---

## Architecture Overview

The spec defines these key architectural decisions:

### Recommendation Engine (SPEC Section 6)
The spec requires a **three-layer architecture**:
- Layer 1: Constraint Satisfaction Programming (binary elimination)
- Layer 2: Content-Based Filtering with **Modular Modality Architecture**:
  - Modality-specific scorers (ImageScorer, VideoScorer, etc.)
  - Cosine similarity per modality, not flat vector
  - UseCaseDefinition composes required modalities for multi-modal workflows
- Layer 3: TOPSIS Multi-Criteria Ranking (5 criteria: content_similarity, hardware_fit, speed_fit, ecosystem_maturity, approach_fit)
- Resolution Cascade: quantization → cpu_offload → substitution → workflow → cloud

**Compare this against `src/services/scoring_service.py` and `src/services/recommendation_service.py` to understand current state.**

### Hardware Detection (SPEC Section 4 + HARDWARE_DETECTION.md)
The spec requires **platform-specific detection** with particular rules for:
- Apple Silicon (memory ceiling, GGUF restrictions, excluded models, memory bandwidth)
- NVIDIA (CUDA compute capability for FP8, form factor/power detection)
- AMD ROCm (experimental status)
- CPU (tier classification, AVX support for GGUF)
- Storage (speed tier for load times, space for model fitting)
- RAM (offload capacity calculation)

**Compare this against `src/services/system_service.py` to understand current state.**

### Onboarding Flow (SPEC Section 5)
The spec requires **dual-path onboarding**:
- Quick path: 5 questions, ~2 minutes
- Comprehensive path: 15-20 tiered questions, ~6 minutes

**Compare this against `src/ui/wizard/setup_wizard.py` to understand current state.**

### Model Database (SPEC Section 7)
The spec defines `data/models_database.yaml` as the source of truth for model data.

**Check where `src/services/recommendation_service.py` actually gets model data.**

---

## File Structure

```
AI-Universal-Suite/
├── data/
│   └── models_database.yaml     # Model definitions (spec Section 7)
├── docs/
│   ├── spec/AI_UNIVERSAL_SUITE_SPEC_v3.md  # SOURCE OF TRUTH
│   ├── plan/PLAN_v3.md          # Task tracker & decisions
│   ├── CLI_AGENT_ONBOARDING.md  # Detailed onboarding prompt
│   └── archived/                # Historical documents
├── src/
│   ├── config/
│   │   ├── manager.py           # Config read/write
│   │   └── resources.json       # Static resources
│   ├── schemas/                 # Dataclasses
│   │   ├── environment.py       
│   │   ├── recommendation.py    
│   │   └── installation.py      
│   ├── services/                # Business logic
│   │   ├── system_service.py    # Hardware detection
│   │   ├── scoring_service.py   # Recommendation scoring
│   │   ├── recommendation_service.py  
│   │   ├── comfy_service.py     
│   │   ├── download_service.py  
│   │   └── shortcut_service.py  
│   ├── ui/
│   │   ├── app.py               # Main window
│   │   ├── wizard/              # Setup wizard
│   │   ├── views/               # Module dashboards
│   │   └── components/          
│   └── utils/
│       └── logger.py
├── CLAUDE.md                    # Claude Code specific context
├── AGENTS.md                    # This file (general agent context)
└── requirements.txt
```

---

## Locked Decisions

These decisions are documented in `docs/plan/PLAN_v3.md` and should not be relitigated:

| Area | Decision | Rationale |
|------|----------|-----------|
| Document structure | Single consolidated spec | One source of truth |
| Onboarding | Dual-path (Quick + Comprehensive) | Self-selected commitment levels |
| Model database | Separate YAML file | 100+ models would bloat spec |
| Cloud APIs | Partner Nodes primary | Unified credits, native to ComfyUI 0.3.60+ |
| Recommendation | 3-layer architecture | Research-validated approach |
| Content Layer | Modular modality architecture | Multi-modal use cases, single responsibility |
| Platform weights | 40% Mac, 40% Windows, 20% Linux | Target user distribution |

## Decision Workflow for Architecture Changes

**Before implementing any architecture/spec change**, follow this workflow:

1. **Document Decision** → Add to `PLAN_v3.md` Section 1 (Decision Log)
2. **Document Deprecations** → Add to `PLAN_v3.md` Section 7 (Deprecation Tracker)
3. **Update Spec** → Modify `AI_UNIVERSAL_SUITE_SPEC_v3.md`
4. **Update Plan** → Add tasks to `PLAN_v3.md` Section 2 (Task Tracker)
5. **Update Agent Files** → `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`
6. **Implement** → Follow Migration Protocol

This ensures all documentation stays in sync with code changes.

---

## Platform Constraints (SPEC Section 4 + HARDWARE_DETECTION.md)

These are non-negotiable technical constraints:

### Apple Silicon
- GGUF K-quants crash MPS - only Q4_0, Q5_0, Q8_0 allowed
- 75% memory ceiling for effective VRAM calculation
- HunyuanVideo excluded (~16 min/clip)
- AnimateDiff is primary video option
- Memory bandwidth affects LLM inference speed

### NVIDIA
- FP8 requires compute capability 8.9+ (RTX 40 series)
- FP4/FP6 requires compute capability 12.0+ (RTX 50 series)
- Must detect CUDA capability
- Form factor detection: sqrt(power_ratio) for laptop performance scaling

### AMD ROCm
- Mark as experimental in UI
- May need HSA_OVERRIDE_GFX_VERSION for RDNA2

### CPU
- Tier classification: HIGH (16+), MEDIUM (8-15), LOW (4-7), MINIMAL (<4) cores
- AVX2 required for GGUF CPU offload
- Affects offload viability and performance

### Storage
- Tiers: FAST (NVMe), MODERATE (SATA SSD), SLOW (HDD)
- Affects model load times and recommendation `speed_fit` criterion
- Space constraints trigger priority-based model fitting

---

## Development Conventions

1. **Strict Separation**: UI files must NEVER contain business logic
2. **Hardware Awareness**: All recommendations validated against hardware constraints
3. **Schemas not Models**: Use `src/schemas/` for dataclasses (avoid "models" confusion with AI models)
4. **Async UI**: Long-running tasks in background threads
5. **Type Hints**: Required on all function signatures
6. **Spec Citations**: Reference spec sections in commit messages and comments

---

## Virtual Environment

```powershell
# Windows
.dashboard_env\venv\Scripts\activate

# macOS/Linux  
source .dashboard_env/venv/bin/activate
```

---

## Your Workflow

1. **Read the spec** for the area you're working on
2. **Compare** spec requirements against current code
3. **Document** gaps you find
4. **Propose** fixes with spec section citations
5. **Implement** after confirming approach
6. **Verify** changes work and align with spec

---

## Communication Style

- Be direct and concise
- Criticism over compliments when reviewing code
- Ask clarifying questions before assuming intent
- Push back with better approaches rather than just executing
- Always cite spec sections when discussing requirements

---

## When Something Seems Wrong

1. Check if the spec addresses it (search the spec document)
2. Check `docs/plan/PLAN_v3.md` for decision history
3. Check `docs/archived/` for context on past iterations
4. If spec seems incorrect, flag it rather than silently diverging
