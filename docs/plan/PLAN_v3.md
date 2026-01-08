# AI Universal Suite - Implementation Plan v3.0

**Status**: Active  
**Last Updated**: January 2026  
**Reference Spec**: `docs/spec/AI_UNIVERSAL_SUITE_SPEC_v3.md`

---

## 0. Current State Assessment

> **Last Audited**: January 2026
> **Auditor**: Claude Code
> The codebase was built during earlier iterations (v1/v2) and needs alignment with SPEC_v3.

### What Matches the Spec ✅

| Component | File(s) | SPEC Section | Notes |
|-----------|---------|--------------|-------|
| Model Database Schema | `data/models_database.yaml` | Section 7 | Follows spec structure with variants, platform_support, capabilities |
| Installation Schemas | `src/schemas/installation.py` | Section 10 | InstallationManifest, InstallationItem align with spec |
| Basic EnvironmentReport | `src/schemas/environment.py` | Section 4 | Has cuda_compute_capability field (not populated) |
| UserProfile/ModelCandidate | `src/schemas/recommendation.py` | Section 10 | Core structures exist (incomplete fields) |
| Wizard UI Components | `src/ui/wizard/components/*` | Section 12 | UseCaseCard, ModuleConfig, ProgressPanel reusable |
| App Structure | `src/ui/app.py`, `src/main.py` | Section 3 | CustomTkinter, service-oriented architecture |
| Logging | `src/utils/logger.py` | Section 11 | Functional, no changes needed |

### What Contradicts the Spec ❌

| Area | Current Code | SPEC Requirement | Location | Impact |
|------|--------------|------------------|----------|--------|
| **Recommendation Architecture** | Single-pass weighted scoring (50% hardware, 35% user, 15% approach) | 3-layer: CSP binary elimination → Content-based cosine similarity → TOPSIS ranking | `scoring_service.py:22-26` | **CRITICAL** - Wrong architecture |
| **Apple Silicon RAM** | Falls back to 16GB on any detection error | Must fail explicitly or use alternative (system_profiler) | `system_service.py:54-55` | **CRITICAL** - Wrong recommendations for 8GB/128GB machines |
| **Memory Ceiling** | Uses 100% of unified memory as VRAM | Must apply 75% ceiling for Apple Silicon | `system_service.py:48` | **HIGH** - Over-recommends models |
| **Model Data Source** | Loads from `resources.json` | Must load from `models_database.yaml` | `recommendation_service.py:165` | **HIGH** - Using wrong/outdated data |
| **Onboarding Flow** | Single use-case-first path | Dual-path: Quick (5 questions) OR Comprehensive (15-20 tiered) | `setup_wizard.py:46-72` | **HIGH** - Missing path selection |
| **CUDA Compute Capability** | Field exists but never populated | Must detect via `torch.cuda.get_device_capability()` | `system_service.py` (missing) | **MEDIUM** - Can't filter FP8 models |
| **K-quant Filtering** | No filtering for MPS | Filter to Q4_0, Q5_0, Q8_0 only (K-quants crash MPS) | Not implemented | **MEDIUM** - Crashes on Apple Silicon |
| **HunyuanVideo Exclusion** | Not excluded for Apple Silicon | Must exclude (~16 min/clip impractical) | Not implemented | **LOW** - Poor UX |

### What's Missing Entirely 🔲

#### Core Architecture Files (Must Create)

| File | SPEC Section | Purpose |
|------|--------------|---------|
| `src/services/constraint_layer.py` | 6.2 | Layer 1: CSP binary elimination |
| `src/services/content_layer.py` | 6.3 | Layer 2: Content-based cosine similarity |
| `src/services/topsis_layer.py` | 6.4 | Layer 3: TOPSIS multi-criteria ranking |
| `src/services/resolution_cascade.py` | 6.5 | Quantization downgrade, variant substitution |
| `src/services/recommendation_explainer.py` | 6.6 | Human-readable explanations |

#### Hardware Detection Files (Must Create)

| File | SPEC Section | Purpose |
|------|--------------|---------|
| `src/services/hardware_detector.py` | 4.1 | Base class with factory method |
| `src/services/apple_silicon_detector.py` | 4.2 | sysctl, chip variant, memory ceiling |
| `src/services/nvidia_detector.py` | 4.3 | nvidia-smi, compute capability, FP8/FP4 support |
| `src/services/amd_rocm_detector.py` | 4.4 | rocminfo, experimental status |
| `src/services/pytorch_installer.py` | CUDA_PYTORCH_INSTALLATION.md | Dynamic PyTorch/CUDA installation |

#### Schema Additions (Must Add)

| Item | SPEC Section | Notes |
|------|--------------|-------|
| `HardwareProfile` dataclass | 4.5 | platform, effective_vram, compute_capability, tier |
| `RejectionReason` dataclass | 6.2 | For constraint layer explanations |
| `ScoredCandidate` dataclass | 6.3 | Content similarity + matching features |
| `RankedCandidate` dataclass | 6.4 | TOPSIS score + criteria breakdown |
| `ResolutionResult` dataclass | 6.5 | For cascade explanations |

#### Onboarding Files (Must Create)

| File | SPEC Section | Purpose |
|------|--------------|---------|
| `src/config/onboarding_questions.yaml` | 5.2-5.3 | Question definitions with show_if conditions |
| `src/ui/wizard/path_selector.py` | 5.1 | Quick vs Comprehensive selection |
| `src/ui/wizard/hardware_display.py` | 5.4 | Hardware confirmation screen |
| `src/ui/wizard/tiered_question_flow.py` | 5.3 | Progressive tiered questions |

#### Missing Features

| Feature | SPEC Section | Current State |
|---------|--------------|---------------|
| Storage type detection | 4.6.2 | Stub returns "unknown" (`system_service.py:114`) |
| Thermal state detection | 4.6.1 | Not implemented |
| Memory bandwidth lookup | 4.2 | Not implemented |
| Power state detection | 4.6 | Stub returns "balanced", False (`system_service.py:122`) |

### Files Requiring Major Changes

| File | Lines | Issues | Action |
|------|-------|--------|--------|
| `src/services/system_service.py` | 184 | 16GB fallback (L54-55), no compute capability detection, no memory ceiling, storage stub | Refactor to platform-specific detectors |
| `src/services/scoring_service.py` | 246 | Entire architecture wrong (single-pass weighted) | **DELETE** - Replace with 3-layer system |
| `src/services/recommendation_service.py` | 247 | Uses resources.json (L165), uses old scoring service | Migrate to YAML, integrate 3 layers |
| `src/ui/wizard/setup_wizard.py` | 241 | No path selection, single flow, use-case first | Implement dual-path per SPEC Section 5 |
| `src/schemas/recommendation.py` | 213 | Missing HardwareProfile, ScoredCandidate, RankedCandidate | Add new dataclasses |

### Files That Can Be Preserved

| File | Status | Notes |
|------|--------|-------|
| `src/schemas/installation.py` | ✅ Keep | Aligns with spec |
| `src/schemas/environment.py` | ⚠️ Extend | Add fields, keep existing |
| `src/ui/wizard/components/use_case_card.py` | ✅ Keep | Reusable component |
| `src/ui/wizard/components/module_config.py` | ✅ Keep | Reusable component |
| `src/ui/wizard/components/progress_panel.py` | ✅ Keep | Reusable component |
| `src/ui/wizard/components/experience_survey.py` | ⚠️ Adapt | May need modification for new flow |
| `data/models_database.yaml` | ✅ Keep | Source of truth, spec-compliant |
| `src/config/resources.json` | ⚠️ Deprecate | Remove model data, keep only non-model resources |
| `src/utils/logger.py` | ✅ Keep | No changes needed |
| `src/ui/app.py` | ✅ Keep | Main window structure fine |
| `src/config/manager.py` | ⚠️ Extend | Add v3 schema support |

### Priority Ranking

1. **CRITICAL**: Fix Apple Silicon RAM detection (wrong recommendations)
2. **CRITICAL**: Implement 3-layer recommendation architecture
3. **HIGH**: Migrate model loading to `models_database.yaml`
4. **HIGH**: Apply 75% memory ceiling for Apple Silicon
5. **HIGH**: Implement dual-path onboarding
6. **MEDIUM**: Add CUDA compute capability detection
7. **MEDIUM**: Implement K-quant filtering for MPS
8. **LOW**: Storage type detection
9. **LOW**: Thermal state detection

---

## 1. Decision Log

Capturing key decisions made during planning and implementation. Reference this when asking "why did we do it this way?"

| Date | Decision | Options Considered | Rationale |
|------|----------|-------------------|-----------|
| 2026-01-03 | Single consolidated SPEC document | A) Single doc B) Modular docs C) Wiki | One source of truth, prevents sync issues |
| 2026-01-03 | Dual-path onboarding (Quick + Comprehensive) | A) Fixed 5 questions B) Progressive 15-20 C) Dual-path | Self-selected commitment; dual path allows both exploration and optimization |
| 2026-01-03 | Tiered progressive for Comprehensive path | Flat 20 questions vs tiered by use case | Reduces cognitive load; users only see relevant questions |
| 2026-01-03 | Separate models.yaml database | Inline in spec vs external file | 100+ models would bloat spec; external file easier to update |
| 2026-01-03 | Partner Nodes as primary cloud integration | A) Unified B) Individual API keys C) Hybrid | Unified credit system simpler UX, native to ComfyUI 0.3.60+ |
| 2026-01-03 | 3-layer recommendation architecture | A) Weighted scoring B) 3-layer hybrid | Research-validated; separates hard constraints from preferences |
| 2026-01-03 | Platform-specific hardware detectors | A) Monolithic B) Per-platform classes | Each platform has unique APIs and constraints |
| 2026-01-03 | Comprehensive hardware detection | A) GPU-only B) GPU+basic C) Full (GPU/CPU/Storage/RAM) | Full detection enables better recommendations (form factor, speed, offload) |
| 2026-01-03 | Form factor via power ratio | A) Binary laptop/desktop B) sqrt(power_ratio) | Physics-grounded; sqrt scaling matches real thermal-limited performance |
| 2026-01-03 | CPU offload in resolution cascade | A) Skip to substitution B) Include offload step | Enables larger models on hardware with good CPU+RAM but limited VRAM |
| 2026-01-03 | Speed fit criterion in TOPSIS | A) 4 criteria B) 5 criteria with speed_fit | Users prioritizing speed get penalized recommendations on slow storage |
| 2026-01-03 | Hardware warnings in explainer | A) Silent constraints B) Explicit warnings | Warnings improve UX by explaining why choices were made and setting expectations |
| 2026-01-03 | Space-constrained adjustment | A) Reject configs B) Auto-adjust by priority | Auto-adjustment with cloud fallback better UX than outright rejection |
| 2026-01-03 | Memory bandwidth for LLM estimates | A) Ignore B) Factor into recommendations | Helps Apple Silicon users understand LLM inference speed expectations |
| 2026-01-03 | Bandwidth-based speed ratio | A) Magic numbers (0.2) B) Bandwidth formula | User requirement: no arbitrary estimates; `speed_ratio = ram_bw / gpu_bw` |
| 2026-01-03 | GPU bandwidth via lookup tables | A) API query B) Static lookup tables | No reliable cross-platform API; lookup tables based on published specs |
| 2026-01-03 | RAM bandwidth via DDR type detection | A) Assume DDR4 B) Detect DDR type + speed | Accurate bandwidth needed for speed ratio; WMI SMBIOSMemoryType + clock speed |
| 2026-01-03 | Nested profiles in HardwareProfile | A) Flat structure B) Nested CPUProfile/RAMProfile/etc | Cleaner separation of concerns; each profile has own tier/methods |
| 2026-01-03 | Shell output normalization utilities | A) Inline handling B) Per-command fixes C) Centralized utilities | PowerShell profiles can interfere with output; centralized `_run_powershell()`, `_extract_number_from_output()`, `_extract_json_from_output()` utilities prevent repeated issues |
| 2026-01-03 | **HardwareTier = effective capacity** | A) VRAM only B) VRAM + offload viability | **CHANGES SPEC** - Tier should reflect actual runnable capacity, not just native GPU; see Extension below |
| 2026-01-07 | **Modular Modality Architecture** | A) Flat ContentPreferences B) Modality-aware scoring C) Nested modality schema + scorers | **CHANGES SPEC** - Use cases can span multiple modalities (image+video, video+audio); each modality needs independent scoring with composable preferences; see Extension below |

### Extension: HardwareTier Calculation (2026-01-03)

**Problem**: Current SPEC_v3 Section 4.5 defines HardwareTier based on VRAM alone:

| Tier | VRAM | Current Definition |
|------|------|-------------------|
| WORKSTATION | 48GB+ | Pure VRAM |
| PROFESSIONAL | 16-47GB | Pure VRAM |
| PROSUMER | 12-15GB | Pure VRAM |
| CONSUMER | 8-11GB | Pure VRAM |
| ENTRY | 4-7GB | Pure VRAM |
| MINIMAL | <4GB | Pure VRAM |

**Issue**: This creates misleading tier classifications:

```
Machine A: 24GB GPU + 64GB RAM + 16-core CPU
  → VRAM-only tier: PROFESSIONAL
  → Effective capacity: ~60GB (with offload)
  → Can actually run: 60GB models (slower)

Machine B: 24GB GPU + 8GB RAM + 4-core CPU
  → VRAM-only tier: PROFESSIONAL
  → Effective capacity: 24GB (no viable offload)
  → Can actually run: 24GB models only

Both classified as "PROFESSIONAL" but have very different capabilities.
```

**Decision**: HardwareTier should reflect **effective capacity** including offload viability.

**Proposed Algorithm**:
```python
def _calculate_tier(self) -> HardwareTier:
    """
    Calculate tier based on effective capacity, not just VRAM.

    Effective capacity = VRAM + usable_offload_capacity (if CPU/RAM support offload)
    """
    # Start with VRAM
    effective_gb = self.vram_gb

    # Add offload capacity if viable
    if self.cpu is not None and self.cpu.can_offload:
        if self.ram is not None and self.ram.usable_for_offload_gb > 4.0:
            effective_gb += self.ram.usable_for_offload_gb

    # Classify based on effective capacity
    if effective_gb >= 48:
        return HardwareTier.WORKSTATION
    elif effective_gb >= 16:
        return HardwareTier.PROFESSIONAL
    # ... etc
```

**Impact on SPEC**:
- Section 4.5 tier table needs updating to reference "effective capacity"
- Tier boundaries remain the same (48/16/12/8/4 GB)
- `vram_gb` field remains for native capacity
- `effective_capacity_with_offload_gb` property already exists

**User Communication**:
- Tier badge should show effective tier
- Tooltip/hover can explain: "PROFESSIONAL tier (24GB native + 36GB offload)"
- Offload models should show slowdown warning regardless of tier

**Open Questions**:
1. Should offload capacity count fully or be discounted (e.g., 50%) due to slowdown?
2. If discounted, what factor? Speed-based (5-10x slower = 10-20% weight)?
3. Should there be separate `native_tier` and `effective_tier` properties?

**Recommendation**: Start with full offload capacity counting, add discount factor in v3.1 if needed based on user feedback.

### Extension: Shell Output Normalization (2026-01-03)

**Problem**: Windows PowerShell profiles can inject text into command output, breaking parsers that expect clean numeric or JSON results.

**Solution**: Centralized utility functions in `src/services/hardware/ram.py` (to be moved to shared location):
- `_run_powershell(command, timeout)`: Runs PowerShell with `-NoProfile` flag, returns cleaned output
- `_extract_number_from_output(output)`: Finds numeric lines in potentially noisy output
- `_extract_json_from_output(output)`: Extracts JSON object from mixed text output

**Integration Scope**:
| File | Current State | Needed |
|------|--------------|--------|
| `ram.py` | Uses utilities ✅ | Done |
| `storage.py` | Manual PowerShell ❌ | Update to use utilities |
| `nvidia.py` | Uses subprocess directly | Already uses `CREATE_NO_WINDOW` |
| `cpu.py` | Windows registry (not PowerShell) | N/A |

**Future Work**: Move utilities to `src/utils/subprocess_utils.py` for cross-module reuse.

### Extension: Modular Modality Architecture (2026-01-07)

**Problem**: Current `ContentPreferences` is a flat dataclass with fields for all modalities (image, video, audio, 3D). This creates several issues:

1. **Multi-modal use cases**: Real workflows often span modalities:
   - Character animation: image (character sheet) + video (animation)
   - Music video: image + video + audio
   - Game assets: image + 3D + video
   - Illustrated story: text + image

2. **Shared vs. modality-specific preferences**:
   - `photorealism`, `artistic_stylization`, `generation_speed` → apply to ALL modalities
   - `motion_intensity`, `temporal_coherence` → video ONLY
   - `holistic_edits`, `localized_edits` → image editing ONLY
   - `character_consistency` → image AND video (character workflows)

3. **Scoring complexity**: Layer 2 currently builds one vector with all dimensions, even when a use case only involves one modality.

**Solution**: Modular architecture with three components:

```
1. MODALITY PREFERENCES (Independent dataclasses)
   ├── SharedQualityPrefs      # photorealism, speed, quality
   ├── ImageModalityPrefs      # editability, pose_control, style_tags
   ├── VideoModalityPrefs      # motion_intensity, temporal_coherence
   ├── AudioModalityPrefs      # (future)
   └── ThreeDModalityPrefs     # (future)

2. USE CASE DEFINITION (Composes modalities)
   UseCaseDefinition:
     - id: "character_animation"
     - required_modalities: ["image", "video"]
     - shared: SharedQualityPrefs
     - image: ImageModalityPrefs (if needed)
     - video: VideoModalityPrefs (if needed)

3. MODALITY SCORERS (Single responsibility)
   ├── ImageScorer.score(candidates, prefs) → scored for image
   ├── VideoScorer.score(candidates, prefs) → scored for video
   └── ContentBasedLayer orchestrates based on required_modalities
```

**Benefits**:
- **Single Responsibility**: Each scorer only knows its modality
- **Open/Closed**: Add audio/3D without touching existing code
- **Composable**: Use cases declare needs, system assembles
- **Testable**: Each modality scorer testable in isolation
- **Scalable**: New modalities = new `ModalityPrefs` + `ModalityScorer`

**Impact on SPEC**:
- Section 6.3 needs modality-aware architecture diagram
- Section 10 needs updated `ContentPreferences` → `UseCaseDefinition` schema
- `content_layer.py` needs modality scorer registry

**Impact on Code**:
- `src/schemas/recommendation.py`: Restructure preferences by modality
- `src/services/recommendation/content_layer.py`: Add modality scorers
- `tests/services/recommendation/test_content_layer.py`: Per-modality tests

**Migration Path**:
1. Create new modality preference dataclasses (additive)
2. Create `UseCaseDefinition` schema (additive)
3. Add modality scorers to `content_layer.py` (additive)
4. Add conversion from old `ContentPreferences` to new schema
5. Deprecate flat `ContentPreferences` (v1.1)
6. Remove old schema (v2.0)

### Extension: Decision Workflow for Architecture Changes (2026-01-07)

**Problem**: Architecture changes have downstream impacts across multiple documents and files. Without a consistent workflow, changes get lost or inconsistently applied.

**Solution**: Before implementing any architecture/spec change, follow this workflow:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 1: DOCUMENT DECISION                                              │
│  ─────────────────────────                                              │
│  Add entry to PLAN_v3.md Section 1 (Decision Log)                       │
│  Include: Date, Decision, Options Considered, Rationale                 │
│  If significant, add Extension section with full details                │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 2: DOCUMENT DEPRECATIONS                                          │
│  ───────────────────────────                                            │
│  Add entry to PLAN_v3.md Section 7 (Deprecation Tracker)                │
│  Include: What's deprecated, Replacement, Remove By version             │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 3: UPDATE SPEC                                                    │
│  ────────────────────                                                   │
│  Update relevant sections in AI_UNIVERSAL_SUITE_SPEC_v3.md              │
│  Add/modify architecture diagrams, schemas, algorithms                  │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 4: UPDATE PLAN                                                    │
│  ─────────────────                                                      │
│  Add implementation tasks to PLAN_v3.md Section 2 (Task Tracker)        │
│  Include: Files to create/modify, test requirements                     │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 5: UPDATE AGENT INSTRUCTIONS                                      │
│  ──────────────────────────────                                         │
│  Update all agent instruction files with new architecture:              │
│  - CLAUDE.md (Claude Code)                                              │
│  - GEMINI.md (Gemini CLI)                                               │
│  - AGENTS.md (General agents)                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 6: IMPLEMENT                                                      │
│  ────────────────                                                       │
│  Only after documentation is complete, begin implementation             │
│  Follow Migration Protocol (docs/MIGRATION_PROTOCOL.md)                 │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why This Order**:
1. **Decision first**: Prevents "forgetting" to document decisions
2. **Deprecations next**: Forces thinking about migration path
3. **Spec before code**: Spec is source of truth
4. **Plan before code**: Tasks are trackable
5. **Agent files**: All AI tools have consistent context
6. **Implementation last**: Prevents drift between docs and code

**When to Use This Workflow**:
- Any change that affects SPEC_v3.md
- Any new schema/dataclass design
- Any new service architecture
- Any deprecation of existing patterns
- NOT needed for: bug fixes, small refactors, adding tests

---

## 2. Task Tracker

### Phase 1: Core Infrastructure (Weeks 1-3)

#### Week 1: Platform Detection ✅ COMPLETE

**Prerequisites**: Read SPEC_v3 Section 4 before starting.

- [x] **CRITICAL**: Fix Apple Silicon RAM detection ✅ 2026-01-03
  - Current: Falls back to 16GB on any error (`system_service.py:~53`)
  - Required: Fail explicitly or use alternative detection (system_profiler)
  - Impact: Wrong recommendations for 8GB and 128GB machines
  - **Done**: `AppleSiliconDetector` with 75% ceiling and explicit failure

- [x] Create `HardwareProfile` dataclass (SPEC Section 4.5) ✅ 2026-01-03
  - Include: platform type, effective VRAM, compute capability, tier classification
  - Add 75% memory ceiling calculation for Apple Silicon
  - **Done**: `src/schemas/hardware.py`

- [x] Implement `HardwareDetector` base class ✅ 2026-01-03
  - Abstract interface for platform-specific detection
  - Factory method to return correct detector for current platform
  - **Done**: `src/services/hardware/base.py`

- [x] Implement `AppleSiliconDetector` ✅ 2026-01-03
  - Use `sysctl -n hw.memsize` for RAM
  - Use `system_profiler SPHardwareDataType` as fallback
  - Detect chip variant (M1/M2/M3/M4, Pro/Max/Ultra)
  - Apply 75% memory ceiling for effective VRAM
  - **Done**: `src/services/hardware/apple_silicon.py`

- [x] Implement `NVIDIADetector` ✅ 2026-01-03
  - Use `nvidia-smi` for VRAM and GPU name
  - Use `torch.cuda.get_device_capability()` for compute capability
  - Flag FP8 support (requires CC 8.9+)
  - **Done**: `src/services/hardware/nvidia.py`

- [x] Implement `AMDROCmDetector` ✅ 2026-01-03
  - Use `rocminfo` or `rocm-smi` for detection
  - Mark as experimental in returned profile
  - **Done**: `src/services/hardware/amd_rocm.py`

- [x] Add storage type detection (NVMe/SATA/HDD) ✅ 2026-01-03
  - **Done**: `src/services/hardware/storage.py`
  - Supports Windows (WMI), macOS (diskutil), Linux (/sys/block)
  - Includes load time estimation utilities

- [x] Add hardware tier classification logic ✅ 2026-01-03
  - WORKSTATION: 48GB+ VRAM (per SPEC_v3 Section 4.5)
  - PROFESSIONAL: 16-48GB VRAM
  - PROSUMER: 12-16GB VRAM
  - CONSUMER: 8-12GB VRAM
  - ENTRY: 4-8GB VRAM
  - MINIMAL: <4GB or CPU only

- [x] Write unit tests for hardware detection ✅ 2026-01-03
  - Mock platform APIs for cross-platform testing
  - Test tier classification boundaries
  - **Done**: `tests/services/test_hardware_detection.py` (41 tests, all passing)

#### Week 2a: Extended Hardware Detection ✅ COMPLETE

**Prerequisites**: Read HARDWARE_DETECTION.md Sections 2-5 before starting.

**Goal**: Complete the hardware profile with form factor, CPU, storage, and RAM data needed by the recommendation engine.

- [x] Implement form factor / sustained performance detection (HARDWARE_DETECTION.md Section 2) ✅ 2026-01-03
  - Detect actual power limit via `nvidia-smi --query-gpu=power.limit`
  - Look up reference TDP from GPU database (`GPU_REFERENCE_TDP` lookup table)
  - Calculate sustained performance ratio using `sqrt(power_ratio)`
  - **Done**: `src/services/hardware/form_factor.py` with `FormFactorProfile` dataclass
  - Flag mobile GPUs in UI with throttling warning via `get_form_factor_warning()`

- [x] Implement CPU detection (HARDWARE_DETECTION.md Section 3) ✅ 2026-01-03
  - Detect physical/logical cores, model name, architecture
  - Detect AVX/AVX2/AVX-512 support (x86 only) via `cpuinfo` library
  - Classify into tiers: HIGH (16+), MEDIUM (8-15), LOW (4-7), MINIMAL (<4)
  - **Done**: `CPUProfile` dataclass in `src/schemas/hardware.py`
  - **Done**: `src/services/hardware/cpu.py` with platform-specific detection

- [x] Extend storage detection to full StorageProfile (HARDWARE_DETECTION.md Section 4) ✅ 2026-01-03
  - Extend existing `storage.py` with `StorageProfile` dataclass
  - Detect total and free space via `shutil.disk_usage()`
  - Estimate read speeds for load time calculations
  - Classify into tiers: FAST, MODERATE, SLOW
  - **Done**: `src/services/hardware/storage.py` with `detect_storage()` function

- [x] Implement RAM offload detection (HARDWARE_DETECTION.md Section 5) ✅ 2026-01-03
  - Detect total and available RAM
  - Calculate usable RAM for model offload: `(available - 4GB) * 0.8`
  - Integrate with CPU tier for offload viability
  - **Done**: `RAMProfile` dataclass with `bandwidth_gbps`, `memory_type` fields
  - **Done**: `src/services/hardware/ram.py` with DDR bandwidth lookup tables
  - **Done**: `calculate_offload_viability()` using bandwidth-based speed ratio (not magic numbers)

- [x] Update GPU detectors with nested profiles ✅ 2026-01-03
  - `NVIDIADetector`: Added CPU, RAM, Storage, FormFactor profiles + GPU bandwidth lookup
  - `AppleSiliconDetector`: Added CPU, RAM, Storage profiles + unified memory bandwidth
  - `AMDROCmDetector`: Added CPU, RAM, Storage profiles + GPU bandwidth lookup
  - `CPUOnlyDetector`: Added CPU, RAM, Storage profiles for CPU-only fallback

- [x] Add memory bandwidth detection ✅ 2026-01-03
  - GPU bandwidth: Lookup tables in `NVIDIADetector.GPU_BANDWIDTH_GBPS`, `AMDROCmDetector.GPU_BANDWIDTH_GBPS`
  - RAM bandwidth: `RAM_BANDWIDTH_GBPS` lookup + `detect_memory_type()` in `ram.py`
  - Speed ratio formula: `speed_ratio = ram_bandwidth / gpu_bandwidth` (no magic numbers)

- [x] Update unit tests for extended hardware detection ✅ 2026-01-03
  - Test form factor detection and performance ratio calculation
  - Test CPU tier classification
  - Test storage tier classification (via storage type)
  - Test RAM offload calculations with encapsulated lookup pattern
  - Test GPU bandwidth lookups (NVIDIA, AMD)
  - **Done**: Added `TestCPUDetection`, `TestRAMDetection`, `TestFormFactorDetection`, `TestGPUBandwidthLookup`

- [x] Create shared subprocess utilities ✅ 2026-01-03
  - `src/utils/subprocess_utils.py` with I/O normalization functions
  - `run_powershell()` with `-NoProfile` for profile isolation
  - `run_command()` for general subprocess execution
  - `extract_number()`, `extract_json()`, `extract_json_array()` for noisy output parsing
  - Updated `ram.py`, `storage.py`, `nvidia.py` to use shared utilities
  - **Done**: Added `tests/utils/test_subprocess_utils.py` with 29 tests

- [x] Document architecture principles ✅ 2026-01-03
  - `docs/ARCHITECTURE_PRINCIPLES.md` - comprehensive coding patterns guide
  - I/O normalization, no magic numbers, lookup tables, encapsulated lookups
  - Nested profile pattern, explicit failure handling
  - Updated `CLAUDE.md` to reference architecture principles in Source of Truth

#### Week 2a+ (Deferred Tasks from Audits) ✅ COMPLETE

**Note**: These tasks were identified during code audits. Completed 2026-01-06.

- [x] Implement thermal detection for Apple Silicon (SPEC §4.6.1) ✅ 2026-01-06
  - Uses `pmset -g therm` to detect CPU speed limit throttling
  - Returns: "nominal", "fair", "serious", "critical"
  - **Done**: `src/services/hardware/apple_silicon.py:236-298`

- [x] Implement thermal detection for AMD ROCm (SPEC §4.6.1) ✅ 2026-01-06
  - Uses `rocm-smi --showtemp` with amd-smi fallback
  - Temperature thresholds: <70°C=nominal, 70-85=fair, 85-95=serious, >95=critical
  - **Done**: `src/services/hardware/amd_rocm.py:305-386`

- [x] Implement real power state detection (SPEC §4.6) ✅ 2026-01-06
  - Windows: ctypes `GetSystemPowerStatus` + `powercfg`
  - macOS: `pmset -g batt` + low power mode detection
  - Linux: `/sys/class/power_supply` + `powerprofilesctl`
  - **Done**: `src/services/system_service.py:103-275`

- [x] Fix legacy code violations (ARCHITECTURE_PRINCIPLES) ✅ 2026-01-06
  - `system_service.py:55-71` - Returns `None` on failure (not 8GB/0)
  - `system_service.py:92-127` - Uses `run_powershell()` with `-NoProfile`
  - `comfy_service.py:93-129` - Uses `run_command()` with proper error handling
  - **Done**: 17 new tests in `tests/services/test_hardware_detection.py`

#### Week 2b: Configuration & Services

**Prerequisites**: Read SPEC_v3 Sections 7, 11 before starting.

**Goal**: Infrastructure for config persistence, model loading, downloads, and recommendation engine stubs.

- [x] Migrate model loading to `models_database.yaml` ✅ 2026-01-06
  - Created `src/services/model_database.py` with full YAML parsing
  - Updated `recommendation_service.py` to use `ModelDatabase`
  - Added `_generate_model_candidates()` with platform/VRAM filtering
  - 37 unit tests in `tests/services/test_model_database.py`
  - **Note**: `resources.json` retained for non-model config (use_cases, modules)

- [x] Implement `ConfigManager` with v3.0 schema ✅ 2026-01-06
  - Schema versioning with migration from v1/v2 to v3
  - Nested key access via dot notation (`preferences.theme`)
  - Installation state tracking (modules, models, custom nodes)
  - Timestamp tracking (created_at, updated_at)
  - 20 TDD tests in `tests/config/test_config_manager.py`

- [ ] Implement `DownloadService` with retry and progress
  - Exponential backoff on failure
  - SHA256 hash verification
  - Progress callback for UI updates
  - Concurrent download queue

- [ ] Implement `ShortcutService` for all platforms
  - Windows: .bat files or Start Menu shortcuts
  - macOS: .command files or .app bundles
  - Linux: .desktop files

- [x] Stub out 3-layer recommendation classes ✅ 2026-01-06
  - `src/services/recommendation/constraint_layer.py` (Layer 1: CSP)
  - `src/services/recommendation/content_layer.py` (Layer 2: Content-Based)
  - `src/services/recommendation/topsis_layer.py` (Layer 3: TOPSIS)
  - Includes dataclasses: `PassingCandidate`, `RejectedCandidate`, `ScoredCandidate`, `RankedCandidate`
  - Full implementation in Phase 3

- [ ] Add logging infrastructure
  - Structured logging with levels
  - File rotation
  - Debug mode for development

- [ ] Integration tests for config persistence

#### Week 3: CUDA/PyTorch Dynamic Installation

**CRITICAL**: This implements the "zero terminal interaction" core principle. Users must never manually install PyTorch/CUDA - the app handles this automatically based on detected GPU.

**Note**: Can run in parallel with Phase 2 if needed, but is NOT optional - it's core to the app's value proposition.

- [ ] Implement CUDA/PyTorch dynamic installation (see `docs/spec/CUDA_PYTORCH_INSTALLATION.md`)
  - Detect NVIDIA compute capability (sm_120 for Blackwell, sm_89 for Ada, etc.)
  - Determine optimal PyTorch/CUDA version for detected GPU
  - Install into venv only (not system Python)
  - Support Blackwell (RTX 5090/5080) with CUDA 12.8+ / 13.x
  - Support FP4/FP6 detection for Blackwell GPUs
  - Verify installation with `torch.cuda.is_available()`
  - Fallback chain: stable → nightly → older CUDA → CPU

### Phase 2: Onboarding System (Weeks 4-5)

**Prerequisites**: Read SPEC_v3 Section 5 before starting.

#### Week 4: Question System
- [ ] Define question schemas in `onboarding_questions.yaml`
- [ ] Implement `QuestionCard` component
- [ ] Implement `OptionGrid` for multi-select
- [ ] Implement `SliderInput` for priority slider
- [ ] Implement `PathSelectorView` (Quick vs Comprehensive)
- [ ] Implement `HardwareDisplayView` (show detected hardware, allow override)

#### Week 5: Tiered Flow
- [ ] Implement `TieredQuestionFlow` widget
- [ ] Implement tier visibility logic (`show_if` conditions)
- [ ] Implement `RecommendationPreview` sidebar
- [ ] Implement `APIKeyInput` with provider selection
- [ ] Connect onboarding to `UserProfile` generation (5 aggregated factors)
- [ ] Integration tests for both paths (Quick + Comprehensive)

### Phase 3: Recommendation Engine (Weeks 6-7)

**Prerequisites**: Read SPEC_v3 Section 6 thoroughly. This replaces the current `scoring_service.py`.

**Dependencies**: Phase 1 Week 2a extended hardware detection must be complete (CPU, Storage, RAM profiles).

#### Week 6: Layers 1 & 2
- [ ] Implement `ConstraintSatisfactionLayer` (SPEC Section 6.2)
  - [ ] VRAM constraint with quantization fallback paths
  - [ ] CPU offload viability check (`_can_offload_to_cpu`) - uses CPU tier + AVX2 + RAM
  - [ ] Platform compatibility checks (Apple Silicon exclusions)
  - [ ] Compute capability requirements (FP8 on CC 8.9+)
  - [ ] Storage space constraint (`_check_storage_constraint`) - uses StorageProfile
  - [ ] Return rejected candidates with reasons
  
- [ ] Implement `ContentBasedLayer` with Modular Modality Architecture (SPEC Section 6.3)
  - [ ] Create modality preference schemas in `recommendation.py`:
    - [ ] `SharedQualityPrefs` (photorealism, artistic_stylization, generation_speed, output_quality, character_consistency)
    - [ ] `ImageModalityPrefs` (editability, pose_control, holistic_edits, localized_edits, style_tags)
    - [ ] `VideoModalityPrefs` (motion_intensity, temporal_coherence, duration_preference)
    - [ ] `AudioModalityPrefs` (stub for future)
    - [ ] `ThreeDModalityPrefs` (stub for future)
  - [ ] Create `UseCaseDefinition` schema (id, name, required_modalities, composed prefs)
  - [ ] Create `ModalityScorer` abstract base class with:
    - [ ] `DIMENSIONS` and `DIMENSION_WEIGHTS` class attributes
    - [ ] `build_user_vector()` abstract method
    - [ ] `build_model_vector()` abstract method
    - [ ] `score()` concrete method with cosine similarity
  - [ ] Implement `ImageScorer(ModalityScorer)` in `content_layer.py`
  - [ ] Implement `VideoScorer(ModalityScorer)` in `content_layer.py`
  - [ ] Update `ContentBasedLayer` to orchestrate modality scorers:
    - [ ] Scorer registry: `Dict[str, ModalityScorer]`
    - [ ] `score_for_use_case(candidates, use_case: UseCaseDefinition)` method
  - [ ] Add conversion from legacy `ContentPreferences` to new schema
  - [ ] Feature matching identification for explainability

#### Week 7: Layer 3 & Resolution
- [ ] Implement `TOPSISLayer` (SPEC Section 6.4)
  - [ ] Decision matrix construction
  - [ ] Vector normalization
  - [ ] Ideal/anti-ideal solution calculation
  - [ ] Closeness coefficient computation (0-1 score)
  - [ ] `speed_fit` criterion - uses StorageProfile for load time estimates
  - [ ] Form factor penalty in `hardware_fit` - uses sustained_performance_ratio
  - [ ] Speed-priority weight adjustment - uses UserPreferences.speed_priority
  
- [ ] Implement `ResolutionCascade` (SPEC Section 6.5)
  - [ ] Quantization downgrade path (FP16 → FP8 → GGUF Q8 → Q5 → Q4)
  - [ ] CPU offload step (`_try_cpu_offload`) - uses CPU tier + RAM
  - [ ] Variant substitution logic
  - [ ] Cloud offload suggestion when local insufficient
  
- [ ] Implement `RecommendationExplainer`
  - [ ] Human-readable reasoning for each recommendation
  - [ ] Constraint rejection explanations
  - [ ] Factor contribution breakdown
  - [ ] Hardware warning generation (SPEC Section 6.7.6)
    - [ ] Form factor / laptop warnings - uses is_laptop + sustained_performance_ratio
    - [ ] Storage speed warnings for speed-focused users - uses storage_tier
    - [ ] CPU offload notifications - when execution_mode == gpu_offload
    - [ ] Low RAM warnings - uses ram_for_offload_gb
    - [ ] AVX2 warnings for GGUF - uses supports_avx2

- [ ] Implement `SpaceConstrainedAdjustment` (SPEC Section 6.7.5)
  - [ ] Priority-based model fitting when storage insufficient
  - [ ] Cloud fallback suggestions for removed models
  - [ ] Space shortage calculations

- [ ] Delete or archive old `scoring_service.py`

- [ ] Comprehensive recommendation tests
  - [ ] All hardware tiers (WORKSTATION → MINIMAL)
  - [ ] All platform types
  - [ ] Edge cases (exact VRAM boundaries, mixed constraints)
  - [ ] Form factor scenarios (desktop vs laptop)
  - [ ] Storage tier scenarios (NVMe vs HDD)

### Phase 4: Model Management (Week 8)

**Dependencies**: Phase 3 recommendation engine should be functional to test model selection.

- [ ] Populate `models_database.yaml` with remaining models
- [ ] Add `hardware` section to model entries (SPEC Section 7.2)
  - [ ] `total_size_gb` - total disk space needed (for space constraint)
  - [ ] `compute_intensity` - "high", "medium", "low" (for form factor penalty)
  - [ ] `supports_cpu_offload` - can layers offload to RAM (for resolution cascade)
  - [ ] `ram_for_offload_gb` - RAM needed if offloading
  - [ ] `supports_tensorrt` - TensorRT optimization available (for speed_fit bonus)
  - [ ] `mps_performance_penalty` - performance penalty on Apple Silicon
- [ ] Implement `ModelDatabase` class with querying/filtering
- [ ] Implement `ModelManagerService`
- [ ] Implement `ModelCard` component
- [ ] Implement download queue with progress UI
- [ ] Implement model deletion with cleanup
- [ ] Add model update checking (compare hashes)
- [ ] Write model management tests

### Phase 5: Cloud Integration (Week 9)

**Prerequisites**: Read SPEC_v3 Section 8 before starting.

- [ ] Implement `PartnerNodeManager`
  - [ ] Account status checking
  - [ ] Service availability listing
  - [ ] Credit balance display
- [ ] Implement `ThirdPartyAPIManager`
  - [ ] Key storage in `ComfyUI/keys/`
  - [ ] Provider configuration UI
- [ ] Implement `CloudOffloadStrategy`
  - [ ] When to suggest cloud vs local
  - [ ] Cost estimation
- [ ] Implement `CloudAPIsView`
- [ ] Write cloud integration tests

### Phase 6: Polish & Testing (Weeks 10-11)

#### Week 10: Integration
- [ ] Full wizard flow integration testing
- [ ] Cross-platform testing
  - [ ] Windows 10/11 + NVIDIA (RTX 20/30/40 series)
  - [ ] macOS + Apple Silicon (M1/M2/M3/M4)
  - [ ] Linux + AMD ROCm (RX 6000/7000)
- [ ] Error handling and recovery flows
- [ ] Performance optimization
- [ ] UI polish and consistency

#### Week 11: Documentation & Release
- [ ] Update all documentation
- [ ] Create user guide
- [ ] Create troubleshooting guide
- [ ] Package for distribution
- [ ] Beta testing
- [ ] Release v1.0

---

## 3. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Apple Silicon GGUF K-quant crashes | High | Medium | Filter to non-K quants (Q4_0, Q5_0, Q8_0) for MPS |
| HuggingFace rate limiting | Medium | High | Retry with exponential backoff; suggest HF token |
| Partner Node API changes | Low | High | Abstract behind service layer; monitor releases |
| Model URLs become stale | Medium | Medium | URL verification on startup; fallback URLs |
| ROCm compatibility issues | High | Low | Warn users; HSA_OVERRIDE env var; mark "experimental" |
| Wrong model recommendations | Medium | High | Extensive testing; user feedback mechanism; easy override |
| Disk space exhaustion | Medium | Medium | Pre-flight space check; staged downloads; cleanup on failure |
| Legacy code conflicts with spec | High | Medium | Document gaps (Section 0); systematic replacement |

---

## 4. Open Questions

| Question | Context | Status |
|----------|---------|--------|
| ~~Document structure~~ | Single vs modular | **Resolved**: Single consolidated spec |
| ~~Onboarding question count~~ | How many questions | **Resolved**: Dual-path (5 quick / 15-20 comprehensive) |
| ~~Cloud API auth model~~ | Unified vs per-provider | **Resolved**: Partner Nodes + third-party keys |
| ~~Model database format~~ | YAML vs JSON vs SQLite | **Resolved**: YAML for human-readability |
| ~~Recommendation architecture~~ | Weighted vs layered | **Resolved**: 3-layer (CSP→Content→TOPSIS) |
| Telemetry opt-in | What to collect, how to present | Open |
| Update mechanism | How to update models/app | Open |
| Workflow bundling | Which workflows to include OOTB | Open |
| Legacy code migration | Gradual vs clean break | Open - see Section 0 |

---

## 5. Progress Summary

**Overall Progress**: Phase 1 (Infrastructure) In Progress

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 0: Planning & Spec | ✅ Complete | 100% |
| Phase 0.5: Codebase Audit | ✅ Complete | 100% |
| Phase 1: Core Infrastructure | 🔄 In Progress | 60% |
| Phase 2: Onboarding System | ⬜ Not Started | 0% |
| Phase 3: Recommendation Engine | ⬜ Not Started | 0% |
| Phase 4: Model Management | ⬜ Not Started | 0% |
| Phase 5: Cloud Integration | ⬜ Not Started | 0% |
| Phase 6: Polish & Testing | ⬜ Not Started | 0% |

---

## 6. Agent Onboarding

If you're an AI agent starting work on this project:

1. **Claude Code**: `CLAUDE.md` is auto-loaded with full context
2. **Gemini CLI**: `GEMINI.md` is auto-loaded with full context
3. **Other agents**: Read `AGENTS.md` for general context
4. **Understand the gaps**: See Section 0 of this document

**Do not trust the existing code to be correct.** Compare everything against the spec.

---

## 7. Deprecation Tracker

See `docs/MIGRATION_PROTOCOL.md` for full migration patterns and procedures.

| File/Function | Deprecated | Replacement | Remove By | Status |
|---------------|------------|-------------|-----------|--------|
| `scoring_service.py` | Pending | 3-layer system (`recommendation/`) | v1.0 | Active - do not use for new code |
| `resources.json` (model sections) | Pending | `models_database.yaml` | v1.0 | Active - migrate reads |
| `system_service.get_gpu_info()` | 2026-01-03 | `HardwareDetector` classes | v1.0 | Migrated - delegates to new detectors |
| `setup_wizard.py` (single path) | Pending | Dual-path flows | v1.0 | Active - wrong architecture |
| `ContentPreferences` (flat schema) | 2026-01-07 | `UseCaseDefinition` + modality prefs | v1.1 | Active - migrate to modular schema |
| `content_layer._build_user_vector()` (flat) | 2026-01-07 | Modality-specific `ModalityScorer` classes | v1.1 | Active - refactor to per-modality |

**Rules:**
- New code must NOT import deprecated modules
- Mark deprecated code with warnings before removal
- Keep deprecated code until v1.0 release minimum

---

## 8. References

| Document | Location | Purpose |
|----------|----------|---------|
| Technical Specification | `docs/spec/AI_UNIVERSAL_SUITE_SPEC_v3.md` | Source of truth |
| Hardware Detection | `docs/spec/HARDWARE_DETECTION.md` | GPU, CPU, Storage, RAM detection |
| CUDA/PyTorch Installation | `docs/spec/CUDA_PYTORCH_INSTALLATION.md` | PyTorch installation logic |
| Architecture Principles | `docs/ARCHITECTURE_PRINCIPLES.md` | Coding patterns and standards |
| Model Database | `data/models_database.yaml` | Model entries with variants |
| Migration Protocol | `docs/MIGRATION_PROTOCOL.md` | How to migrate/deprecate code |
| Claude Code Context | `CLAUDE.md` | Auto-loaded by Claude Code |
| Gemini CLI Context | `GEMINI.md` | Auto-loaded by Gemini CLI |
| General Agent Context | `AGENTS.md` | For other AI tools (Cursor, Aider, etc.) |
| Research | `docs/archived/research/` | Background research documents |
| ~~Outstanding Issues~~ | `docs/archived/audits/OUTSTANDING_ISSUES_2026-01-06.md` | **ARCHIVED** - See Section 9 |

---

## 9. Issue Tracker (Integrated)

> **Supersedes**: `docs/archived/audits/OUTSTANDING_ISSUES_2026-01-06.md` (archived)
> All issues now tracked here with full context, spec references, and plan mappings.

### 9.1 Issue → Plan → Spec Mapping

| Priority | Issue | Plan Location | SPEC Section | Status |
|----------|-------|---------------|--------------|--------|
| **CRITICAL** | scoring_service.py uses old algorithm | Phase 3 Week 6 | §6 | Stubs ready, blocked by Phase 3 |
| **CRITICAL** | Resolution cascade not implemented | Phase 3 Week 7 | §6.5 | Stub exists |
| **CRITICAL** | models_database.yaml missing hardware section | Phase 4 Week 8 | §7.2 | Schema defined, data missing |
| **HIGH** | Dual-path onboarding not implemented | Phase 2 Week 4-5 | §5.1-5.2 | Not started |
| **HIGH** | show_if expression evaluator missing | Phase 2 Week 5 | §5.3 | Not started |
| ~~**HIGH**~~ | ~~Apple Silicon thermal returns None~~ | Phase 1 Week 2a+ | §4.6.1 | ✅ Resolved 2026-01-06 |
| ~~**HIGH**~~ | ~~AMD ROCm thermal returns None~~ | Phase 1 Week 2a+ | §4.6.1 | ✅ Resolved 2026-01-06 |
| ~~**HIGH**~~ | ~~Power state detection placeholder~~ | Phase 1 Week 2a+ | §4.6 | ✅ Resolved 2026-01-06 |
| ~~**HIGH**~~ | ~~Silent fallbacks in system_service.py~~ | Week 2a+ cleanup | ARCH_PRINCIPLES | ✅ Resolved 2026-01-06 |
| **MEDIUM** | DownloadService incomplete | Phase 1 Week 2b | §11.3 | Not started |
| **MEDIUM** | ShortcutService incomplete | Phase 1 Week 2b | §11.5 | Not started |
| **MEDIUM** | PyTorch/CUDA dynamic installation | Phase 1 Week 3 | CUDA_PYTORCH_INSTALLATION.md | **CRITICAL for zero-terminal** |
| **MEDIUM** | Magic numbers undocumented | Ongoing | ARCH_PRINCIPLES | See list below |
| **MEDIUM** | Config integration tests | Phase 1 Week 2b | §11.4 | Unit tests done |
| **MEDIUM** | Cloud API pricing gaps | Phase 5 Week 9 | §8.2.3 | Spec incomplete |
| **DOC** | ARCHITECTURE_PRINCIPLES.md not in spec | - | §1 | Needs reference |
| **DOC** | show_if syntax not formally defined | - | §5.3 | Needs spec section |
| **DOC** | ConfigManager schema not in spec | - | §11.4 | Implemented, undocumented |

### 9.2 Spec Sections Not Yet in Plan

| SPEC Section | Description | Recommended Phase | Priority |
|--------------|-------------|-------------------|----------|
| §4.6 | Power State Detection | Phase 1 Week 2a+ | MEDIUM |
| §4.6.1 | Thermal State Detection | Phase 1 Week 2a+ | LOW |
| §6.7.7 | Memory Bandwidth LLM Estimation | Phase 3 | LOW |
| §8.2.3 | Image API Pricing Matrix | Phase 5 | LOW |
| §9.4 | Model Manager View UI mockup | Phase 4 | MEDIUM |
| §12.3 | Model Manager Components | Phase 4 | MEDIUM |

### 9.3 Magic Numbers Requiring Documentation

| Location | Value | Purpose | Action |
|----------|-------|---------|--------|
| `ram.py:249` | `4.0` GB | OS reserved memory | Add constant `OS_RESERVED_RAM_GB` |
| `ram.py:252` | `0.8` | Safety factor for offload | Add constant `OFFLOAD_SAFETY_FACTOR` |
| `scoring_service.py:125` | `-0.20` | Thermal throttle penalty | DELETE with scoring_service.py |
| `scoring_service.py:129` | `-0.15` | Storage overuse penalty | DELETE with scoring_service.py |
| `scoring_service.py:164` | `(val-1)/4` | Preference normalization | DELETE with scoring_service.py |
| `recommendation_service.py:124` | `1.5` GB | Venv size estimate | Add constant `VENV_SIZE_ESTIMATE_GB` |
| SPEC §6.5 | `5x/10x` | CPU offload slowdown | Add benchmark or formula |

### 9.4 Tasks Missing from Plan (Add to Phase 1)

These tasks are in OUTSTANDING_ISSUES.md but not explicitly in the plan:

```
Phase 1 Week 2a+ (Add):
- [ ] Implement thermal detection for Apple Silicon (IOKit)
- [ ] Implement thermal detection for AMD ROCm (rocm-smi)
- [ ] Implement real power state detection (battery vs AC)
- [ ] Fix silent fallbacks in system_service.py
- [ ] Fix direct subprocess in comfy_service.py:100

Phase 1 Week 3 (MANDATORY - not optional):
- [ ] Implement PyTorch/CUDA dynamic installation
  - get_pytorch_config(compute_capability) → cu130/cu121/cu118
  - install_pytorch(config) → pip install into venv
  - Version matrix: Blackwell→cu130, Ada→cu130, Volta→cu121, Pascal→cu118
  - Fallback chain: stable → nightly → older CUDA → CPU
  - Verification: torch.cuda.is_available()
```

### 9.5 Resolved Issues

| Issue | Resolution | Date | Commit |
|-------|------------|------|--------|
| 3-layer files missing | Created stubs in `src/services/recommendation/` | 2026-01-06 | bec633d |
| Model database wrong source | Created `ModelDatabase` class | 2026-01-06 | bec633d |
| ConfigManager v1 flat structure | Upgraded to v3.0 with migration | 2026-01-06 | bec633d |
| SPEC §6.1 lists 4 criteria | Updated to show all 5 | 2026-01-06 | - |
| HardwareTier effective capacity | Updated HARDWARE_DETECTION.md | 2026-01-06 | - |
| Deprecation tracker missing | Added Section 7 to PLAN | 2026-01-06 | - |
| Apple Silicon thermal returns None | Implemented via `pmset -g therm` | 2026-01-06 | - |
| AMD ROCm thermal returns None | Implemented via `rocm-smi --showtemp` | 2026-01-06 | - |
| Power state detection placeholder | Platform-specific detection (Win/Mac/Linux) | 2026-01-06 | - |
| Silent fallbacks in system_service.py | Returns None on failure, uses run_powershell() | 2026-01-06 | - |

### 9.6 Metrics

| Category | Total | Resolved | Remaining |
|----------|-------|----------|-----------|
| Critical | 3 | 0 | 3 |
| High | 6 | 4 | 2 |
| Medium | 7 | 0 | 7 |
| Documentation | 3 | 0 | 3 |
| **Total** | **19** | **4** | **15** |

*Note: Metrics exclude items that will be deleted (scoring_service.py magic numbers).*

---

## 10. UI Separation of Concerns

> **Purpose**: Clearly define which features belong in the Setup/Installation Wizard vs the Post-Setup Dashboard.
> This prevents scope creep during Phase 2/3 implementation.

### 10.1 Setup Wizard (Phase 2) - One-Time Configuration

The wizard runs **once** during initial setup. Its sole purpose is to configure the system.

| Feature | Rationale | SPEC Section |
|---------|-----------|--------------|
| Hardware detection display | Users confirm detected hardware | §5.4 |
| Path selection (Quick/Comprehensive) | User commitment level | §5.1 |
| Use case selection | Primary workflow preferences | §5.2 |
| Experience questions (Comprehensive) | Fine-tune recommendations | §5.3 |
| Model tier recommendations | Initial model selection | §6 |
| Installation progress | Download/setup tracking | §10 |
| ComfyUI installation | One-time setup | §3 |
| PyTorch/CUDA installation | One-time per hardware | CUDA_PYTORCH |
| Desktop shortcut creation | One-time convenience | §11.5 |
| API key entry (optional) | One-time credential storage | §8.3 |

**NOT in Wizard**:
- Estimated generation times (requires runtime data)
- Model performance metrics (requires actual inference)
- Recommendation refinement (post-setup activity)
- Model management (add/remove models over time)
- Usage analytics (accumulated over time)

### 10.2 Post-Setup Dashboard (Phase 4+) - Ongoing Operations

The dashboard is the **main UI** after setup completes. It supports ongoing model management.

| Feature | Rationale | SPEC Section |
|---------|-----------|--------------|
| **Model Manager** | | §9.4 |
| - Installed models list | Current state visibility | §9.4 |
| - Estimated generation time | Runtime performance data | §6.7.7 |
| - Model comparison | Side-by-side capabilities | TBD |
| - Download new models | Post-setup expansion | §11.3 |
| - Delete models | Storage management | §9.4 |
| - Model update checking | Version management | TBD |
| **Performance Insights** | | NEW |
| - Inference speed estimates | LLM tok/s based on bandwidth | §6.7.7 |
| - Memory pressure warnings | Runtime monitoring | NEW |
| - Thermal state display | Live hardware status | §4.6.1 |
| **Recommendation Refinement** | | NEW |
| - "Recommend more models" | Iterative discovery | NEW |
| - Feedback on recommendations | Quality improvement | NEW |
| - Alternative suggestions | When current models underperform | §6.5 |
| **Cloud Integration** | | §8 |
| - Partner Node balance | Credit tracking | §8.2 |
| - API usage monitoring | Cost tracking | NEW |
| - Cloud vs local toggle | Per-workflow setting | §8.4 |

### 10.3 Feature → Phase Mapping

| Feature | Phase | Files Affected |
|---------|-------|----------------|
| Wizard hardware display | Phase 2 | `hardware_display.py` |
| Wizard path selection | Phase 2 | `path_selector.py` |
| Wizard question flow | Phase 2 | `tiered_question_flow.py` |
| Wizard recommendations | Phase 3 | `recommendation/` layers |
| Model Manager view | Phase 4 | `model_manager_view.py` |
| Performance insights | Phase 4 | `performance_view.py` (NEW) |
| Estimated gen time | Phase 4 | Uses `speed_fit` + bandwidth |
| Cloud dashboard | Phase 5 | `cloud_apis_view.py` |

### 10.4 Data Flow: Wizard → Dashboard

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SETUP WIZARD (Phase 2)                       │
│                                                                     │
│  1. Detect Hardware ──► HardwareProfile saved to config            │
│  2. User Answers ──► UserProfile saved to config                   │
│  3. Run Recommendation ──► Selected models saved to config         │
│  4. Install Models ──► installation.models_installed[]             │
│  5. Complete ──► installation.status = "complete"                  │
│                                                                     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    POST-SETUP DASHBOARD (Phase 4+)                  │
│                                                                     │
│  ConfigManager.get("installation.models_installed")                │
│  ConfigManager.get("user_profile")                                 │
│  ConfigManager.get("hardware")  ◄── May re-detect for updates      │
│                                                                     │
│  NEW DATA:                                                          │
│  - Actual inference benchmarks (optional, Phase 6)                 │
│  - Usage statistics                                                │
│  - Model feedback                                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 11. Best Practices Integration

> **Purpose**: Ensure Phase 3 implementation follows established patterns.
> Reference: `docs/ARCHITECTURE_PRINCIPLES.md`

### 11.1 Recommendation Engine Best Practices

| Practice | Implementation | Files |
|----------|----------------|-------|
| **No magic numbers** | All thresholds as named constants | All layers |
| **Lookup tables** | GPU bandwidth, RAM bandwidth | Already in `nvidia.py`, `ram.py` |
| **Explicit failure** | Layer errors raise, don't fallback | `constraint_layer.py` |
| **Dataclasses** | All results as typed dataclasses | `PassingCandidate`, `RankedCandidate` |
| **Testability** | Dependency injection of ModelDatabase | Constructor injection |

### 11.2 Phase 3 Testing Requirements

Each layer must have:

| Test Category | Coverage Target | Notes |
|---------------|-----------------|-------|
| Unit tests per method | 100% | Mock `ModelDatabase` |
| Hardware tier variations | All 6 tiers | WORKSTATION → MINIMAL |
| Platform variations | All 4 platforms | NVIDIA, Apple, AMD, CPU-only |
| Edge cases | Boundaries | Exact VRAM limits, 0 candidates |
| Integration | Layers chained | Pass Layer 1 output to Layer 2 |

### 11.3 Caching Strategy (Phase 6 Enhancement)

Recommendation results can be cached for performance:

```python
# Future enhancement - not in Phase 3 MVP
@lru_cache(maxsize=128)
def get_recommendations(hardware_hash: str, profile_hash: str) -> List[RankedCandidate]:
    ...
```

Cache invalidation triggers:
- Hardware profile change
- User profile change
- Model database update
- 24 hours elapsed

### 11.4 Metrics Collection (Phase 6 Enhancement)

Track recommendation quality for future improvement:

| Metric | Purpose | Collection Point |
|--------|---------|------------------|
| `candidates_passed_layer1` | Filter effectiveness | After CSP |
| `rejection_reasons` | Common constraints | CSP rejections |
| `topsis_score_distribution` | Score health | Layer 3 output |
| `user_override_count` | Recommendation accuracy | Dashboard |

---

*This is a living document. Update as tasks complete and decisions are made.*
