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

#### Week 2a: Extended Hardware Detection

**Prerequisites**: Read HARDWARE_DETECTION.md Sections 2-5 before starting.

**Goal**: Complete the hardware profile with form factor, CPU, storage, and RAM data needed by the recommendation engine.

- [ ] Implement form factor / sustained performance detection (HARDWARE_DETECTION.md Section 2)
  - Detect actual power limit via `nvidia-smi --query-gpu=power.limit`
  - Look up reference TDP from GPU database
  - Calculate sustained performance ratio using sqrt(power_ratio)
  - **Update `HardwareProfile`**: Add `sustained_performance_ratio`, `power_limit_watts`, `reference_tdp_watts`, `is_laptop`
  - Flag mobile GPUs in UI with throttling warning

- [ ] Implement CPU detection (HARDWARE_DETECTION.md Section 3)
  - Detect physical/logical cores, model name, architecture
  - Detect AVX/AVX2/AVX-512 support (x86 only)
  - Classify into tiers: HIGH (16+), MEDIUM (8-15), LOW (4-7), MINIMAL (<4)
  - **Create `CPUProfile` dataclass** in `src/schemas/hardware.py`
  - **Update `HardwareProfile`**: Add CPU fields or nested CPUProfile

- [ ] Extend storage detection to full StorageProfile (HARDWARE_DETECTION.md Section 4)
  - Extend existing `storage.py` with StorageProfile dataclass
  - Detect total and free space
  - Estimate read speeds for load time calculations
  - Classify into tiers: FAST, MODERATE, SLOW
  - **Update `HardwareProfile`**: Add storage fields or nested StorageProfile

- [ ] Implement RAM offload detection (HARDWARE_DETECTION.md Section 5)
  - Detect total and available RAM
  - Calculate usable RAM for model offload
  - Integrate with CPU tier for offload viability
  - **Update `HardwareProfile`**: Add `ram_available_gb`, `ram_for_offload_gb`

- [ ] Update unit tests for extended hardware detection
  - Test form factor detection and performance ratio calculation
  - Test CPU tier classification
  - Test storage tier classification
  - Test RAM offload calculations

#### Week 2b: Configuration & Services

**Prerequisites**: Read SPEC_v3 Sections 7, 11 before starting.

**Goal**: Infrastructure for config persistence, model loading, downloads, and recommendation engine stubs.

- [ ] Migrate model loading to `models_database.yaml`
  - Update `recommendation_service.py` to load from YAML
  - Remove model definitions from `resources.json`
  - Implement `ModelDatabase` class with querying
  
- [ ] Implement `ConfigManager` with v3.0 schema
  - User preferences persistence
  - Installation state tracking
  - Migration from older config versions

- [ ] Implement `DownloadService` with retry and progress
  - Exponential backoff on failure
  - SHA256 hash verification
  - Progress callback for UI updates
  - Concurrent download queue

- [ ] Implement `ShortcutService` for all platforms
  - Windows: .bat files or Start Menu shortcuts
  - macOS: .command files or .app bundles
  - Linux: .desktop files

- [ ] Stub out 3-layer recommendation classes
  - `src/services/recommendation/constraint_layer.py` (Layer 1: CSP)
  - `src/services/recommendation/content_layer.py` (Layer 2: Content-Based)
  - `src/services/recommendation/topsis_layer.py` (Layer 3: TOPSIS)
  - These will be implemented in Phase 3

- [ ] Add logging infrastructure
  - Structured logging with levels
  - File rotation
  - Debug mode for development

- [ ] Integration tests for config persistence

#### Week 3 (Optional): CUDA/PyTorch Installation

**Note**: Can be deferred if blocking other work. PyTorch installation is only needed for actual model inference, not for recommendation engine development. Can run in parallel with Phase 2.

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
  
- [ ] Implement `ContentBasedLayer` (SPEC Section 6.3)
  - [ ] User feature vector construction (from 5 aggregated factors)
  - [ ] Model capability vector construction
  - [ ] Cosine similarity calculation
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
| Model Database | `data/models_database.yaml` | Model entries with variants |
| Migration Protocol | `docs/MIGRATION_PROTOCOL.md` | How to migrate/deprecate code |
| Claude Code Context | `CLAUDE.md` | Auto-loaded by Claude Code |
| Gemini CLI Context | `GEMINI.md` | Auto-loaded by Gemini CLI |
| General Agent Context | `AGENTS.md` | For other AI tools (Cursor, Aider, etc.) |
| Research | `docs/archived/research/` | Background research documents |

---

*This is a living document. Update as tasks complete and decisions are made.*
