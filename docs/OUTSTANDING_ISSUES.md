# Outstanding Issues

Consolidated from architectural audits (2026-01-06). Updated after Phase 1 Week 2b completion.

---

## Priority 1: Critical (Blocking Future Phases)

### CODE: Recommendation Engine Integration
- [ ] **scoring_service.py still uses old algorithm** - 3-layer stubs exist but not integrated
  - Location: `src/services/scoring_service.py`
  - Issue: Single-pass weighted (50/35/15) instead of CSP → Content → TOPSIS
  - Blocked by: Phase 3 implementation
  - Stubs ready: `src/services/recommendation/`

### CODE: Resolution Cascade Not Implemented
- [ ] **No fallback chain**: quantization → CPU offload → substitution → cloud
  - Location: `src/services/recommendation/constraint_layer.py`
  - Issue: Hard rejection only, no progressive degradation
  - Impact: Users with edge-case hardware get no recommendations

### DATA: Missing YAML Schema Fields
- [ ] **models_database.yaml missing hardware section**
  - Required fields per SPEC §7:
    ```yaml
    hardware:
      compute_intensity: "high|medium|low"
      mps_performance_penalty: 0.15
      supports_cpu_offload: true
      ram_for_offload_gb: 16.0
    ```
  - Impact: Cannot calculate laptop penalties or Apple Silicon adjustments

---

## Priority 2: High (Spec Compliance)

### CODE: Onboarding System Incomplete
- [ ] **Dual-path not implemented** (Quick 5 min / Comprehensive 15-20 questions)
  - Location: `src/ui/wizard/setup_wizard.py`
  - Issue: Single linear path only
  - Spec reference: SPEC_v3 §5

- [ ] **show_if expression evaluator missing**
  - Issue: No conditional question rendering
  - Impact: All users see identical flow regardless of selections

### CODE: Thermal Detection Gaps
- [ ] **Apple Silicon thermal**: Returns `None`
  - Location: `src/services/hardware/apple_silicon.py:243`
  - Note: Stub exists, needs IOKit implementation

- [ ] **AMD ROCm thermal**: Returns `None`
  - Location: `src/services/hardware/amd_rocm.py:311`
  - Note: Needs rocm-smi integration

### CODE: Power State Detection
- [ ] **Placeholder implementation**
  - Location: `src/services/system_service.py:108`
  - Issue: Returns hardcoded `("balanced", False)`
  - Impact: Cannot detect battery vs AC power

### CODE: Legacy Code Violations
- [ ] **Silent fallbacks in system_service.py**
  - Line 61: Silent 8GB RAM fallback (violates Explicit Failure principle)
  - Line 70: Silent 0 disk free fallback
  - Line 83: PowerShell without `-NoProfile`

- [ ] **Direct subprocess in comfy_service.py**
  - Line 100: Uses `subprocess.check_call` instead of `run_command()`

---

## Priority 3: Medium (Quality/Completeness)

### CODE: Magic Numbers
- [ ] `ram.py:249` - `4.0` GB reserved for OS (undocumented)
- [ ] `ram.py:252` - `0.8` safety factor for offload (undocumented)
- [ ] `scoring_service.py:125` - `-0.20` thermal throttle penalty
- [ ] `scoring_service.py:129` - `-0.15` storage overuse penalty
- [ ] `scoring_service.py:164` - `(val-1)/4` preference normalization
- [ ] `recommendation_service.py:124` - `1.5` GB venv size estimate
- [ ] SPEC §6.5 - CPU offload slowdown factors (5x/10x) need formula or benchmark

### CODE: Week 2b Remaining Tasks
- [ ] **DownloadService** - Retry logic, SHA256 verification, progress callbacks
- [ ] **ShortcutService** - Cross-platform (.bat/.command/.desktop)
- [ ] **Integration tests** - Config persistence (unit tests done, integration pending)

### CODE: PyTorch/CUDA Dynamic Installation ⚠️ CORE VALUE PROP
- [ ] **Installation logic not implemented** (detection IS implemented)
  - Spec: `docs/spec/CUDA_PYTORCH_INSTALLATION.md` (complete)
  - What EXISTS: `nvidia.py` detects compute capability (8.9, 12.0, etc.)
  - What's MISSING:
    - `get_pytorch_config(compute_capability)` → returns cu130/cu121/cu118
    - `install_pytorch(config)` → pip install into venv
    - Version matrix: Blackwell→cu130, Ada→cu130, Volta→cu121, Pascal→cu118
  - **CRITICAL**: This is core to "zero terminal interaction" principle
  - Impact: Without this, users must manually install PyTorch - defeats app purpose
  - Priority: Should be Phase 1 Week 3 (not optional)

### DATA: Cloud API Pricing Gaps
- [ ] **SPEC §8.2.3 Image API pricing matrix** - Only video detailed
- [ ] **Audio/3D cloud services** - Not specified

---

## Priority 4: Documentation

### SPEC: Internal Contradictions
- [ ] **§6.1 vs §6.7.2**: Says 4 TOPSIS criteria, shows 5 weights → Update §6.1 to say 5
- [ ] **PLAN §1 vs SPEC §4.5**: "effective capacity" vs "VRAM-only" → Decision logged but spec not updated

### SPEC: Orphaned Content (Not in Plan)
- [ ] §4.6.1 Thermal State Detection - No implementation tasks
- [ ] §4.6 Power State Detection - Placeholder only
- [ ] §6.7.7 Memory Bandwidth LLM Estimation - Formula exists, no integration
- [ ] §8.2.3 Image API Pricing matrix - Incomplete
- [ ] §9.4 Model Manager View UI mockup - No code
- [ ] §12.3 Model Manager Components code - Not implemented

### PLAN: Items Without Spec Grounding
- [ ] "Migration from older config versions" - Now implemented but spec doesn't describe schema
- [ ] "Model update checking (compare hashes)" - Phase 4 Week 8, no spec detail
- [ ] Cross-platform testing specifics - Phase 6 Week 10, no strategy doc

### DOCS: Missing Documentation
- [ ] Test plan/strategy document
- [ ] UI mockups/wireframes
- [ ] Error message specifications
- [ ] CI/CD pipeline documentation
- [ ] Performance tuning guide

### DOCS: Cross-Reference Gaps
- [ ] ARCHITECTURE_PRINCIPLES.md not referenced from SPEC_v3 §1
- [ ] show_if expression syntax not formally defined

---

## Resolved Issues (This Session)

| Issue | Resolution | Date |
|-------|------------|------|
| 3-layer files missing | Created stubs in `src/services/recommendation/` | 2026-01-06 |
| Model database wrong source | Created `ModelDatabase` class, integrated with `recommendation_service.py` | 2026-01-06 |
| ConfigManager v1 flat structure | Upgraded to v3.0 with migration support | 2026-01-06 |
| 5 TOPSIS criteria missing | Added to `topsis_layer.py` stub | 2026-01-06 |

---

## Metrics

| Category | Total | Resolved | Remaining |
|----------|-------|----------|-----------|
| Critical | 3 | 0 | 3 |
| High | 6 | 0 | 6 |
| Medium | 10 | 0 | 10 |
| Documentation | 15 | 0 | 15 |
| **Total** | **34** | **0** | **34** |

*Note: "Resolved" counts issues fully closed, not stubbed/partial.*

---

## Next Actions (Recommended Order)

1. Complete Week 2b: DownloadService, ShortcutService
2. Add missing YAML fields to `models_database.yaml`
3. Document magic numbers or convert to named constants
4. Update SPEC §6.1 to say 5 TOPSIS criteria
5. Begin Phase 2: Onboarding dual-path
