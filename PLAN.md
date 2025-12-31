# 🗺️ Project Roadmap: AI Universal Suite v2.0 (Refined)

**Current Status**: Phase 1 (Re-Architecture & Data Modeling).
**Objective**: Implement a robust, adaptive, and data-driven recommendation engine as per Spec Section 13.

---

## Phase 1: Robust Data Modeling & Algorithm Design (IN PROGRESS)
**Priority: CRITICAL - Foundation for Adaptive Logic.**

*   [x] **UI Crash Fix**: Fixed `messagebox` import in `src/ui/views/comfyui.py`.
*   [x] **Apple Silicon Fix**: Rewrote `SystemService.get_gpu_info()` to use `sysctl` logic.
*   [x] **Hardware Scanning**: Implemented `scan_full_environment()` returning `EnvironmentReport`.
*   [ ] **Detailed Data Schemas**:
    *   Expand `UserProfile` to include 1-5 capability scores (Speed, Quality, Consistency, etc.).
    *   Define `ModelCapabilityScores` (0.0-1.0 normalized metrics).
    *   Define `CLICandidate` with capability tags for weighted scoring.
*   [ ] **Scoring Configuration**:
    *   Update `resources.json` to include `recommendation_config` (Weights, Penalties, Bonuses).
    *   Add scoring metadata to CLI Providers (e.g., `coding: 0.9`, `creative_writing: 0.7`).

## Phase 2: Core Services Implementation
**Objective**: Build the logic layer that consumes the Phase 1 Data Models.

*   [ ] **Scoring Engine**: Create `src/services/scoring_service.py` implementing the algorithm from Spec Section 13.5.
    *   Input: `UserProfile`, `HardwareConstraints`, `List[Candidate]`.
    *   Output: `RankedCandidates` with detailed reasoning trace.
*   [ ] **Download Service**: Create `src/services/download_service.py` with robust retry/hash logic.
*   [ ] **Shortcut Service**: Create `src/services/shortcut_service.py`.

## Phase 3: Setup Wizard UI
**Objective**: Collect the high-resolution user data required by the Scoring Engine.

*   [ ] **Survey Architecture**: Create `src/ui/wizard/` with specific stages for:
    *   **Experience Assessment**: Collect `ai_experience` and `technical_experience` (1-5).
    *   **Content Preferences**: Collect `photorealism`, `speed_priority`, `editing_needs` (1-5).
*   [ ] **Live Feedback**: Display "Hardware Constraints" vs "User Desires" gaps in real-time during the review step.

## Phase 4: Integration & Dynamic Mapping
**Objective**: Connect the Recommendation Engine to the Installer.

*   [ ] **Dynamic Manifest**: `ComfyService` generates manifests *dynamically* based on the `ScoringEngine` output, not hardcoded paths.
*   [ ] **CLI Provisioning**: Auto-select and configure the best CLI provider (Claude/Gemini) based on user's `coding` vs `writing` weights.

---

## 5. Technical Constraints & Validation
*   **No Hardcoding**: All scoring weights must live in `resources.json`, not Python code.
*   **Validation Metrics**:
    *   Verify "Expert" profile selects Flux/SDXL.
    *   Verify "Beginner" + "Low VRAM" selects SD1.5 + Quantization.
    *   Verify "Coding" intent selects Claude/Codex over Gemini (if weights dictate).
*   **Unit Tests**: `tests/test_scoring.py` must exist to validate the algorithm math.
