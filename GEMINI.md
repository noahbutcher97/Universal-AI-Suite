# AI Universal Suite v2.0

## Project Overview

**AI Universal Suite** is a cross-platform (Windows, macOS, Linux) desktop application that transforms a user's computer into a fully configured AI workstation through a single, guided setup wizard.

**Core Principle:** The user should never need to open a terminal, write code, or understand technical implementation details. Every action should be achievable through GUI interactions.

## Architecture & Tech Stack

*   **Language**: Python 3.10+
*   **GUI Framework**: [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
*   **Architecture**: Service-Oriented Architecture (SOA) with a strict separation between UI, Logic (Services), and Data (Schemas).
*   **Configuration**: JSON-based config stored in `src/config/resources.json` (static resources) and user config in `~/.ai_universal_suite/config.json`.

### Module System
The application is organized around **modules**:
*   `cli_provider`: Command-line AI assistants (Gemini, Claude).
*   `comfyui`: Visual AI generation (ComfyUI + Custom Nodes).
*   `lm_studio`: Local LLM inference (Planned).
*   `mcp_servers`: Model Context Protocol servers (Planned).

## File Structure & Conventions

```
src/
├── config/                 # Configuration management
│   ├── manager.py          # Config read/write logic
│   └── resources.json      # Static definitions (models, workflows, constraints)
├── schemas/                # Data structures (Dataclasses) - Replaces 'models' to avoid AI confusion
│   ├── environment.py      # EnvironmentReport
│   └── recommendation.py   # UserProfile, RecommendationResult
├── services/               # Core business logic (Pure Python, no UI)
│   ├── system_service.py   # Hardware detection (VRAM, RAM, Storage)
│   ├── comfy_service.py    # ComfyUI installation & management
│   ├── recommendation_service.py # Scoring & decision engine
│   ├── download_service.py # Robust file downloading
│   └── shortcut_service.py # Desktop shortcut generation
├── ui/                     # Presentation Layer (CustomTkinter)
│   ├── app.py              # Main Application Window
│   ├── wizard/             # Setup Wizard (Modal)
│   └── views/              # Module-specific dashboards
└── workflows/              # Bundled JSON workflow templates
```

### Development Conventions
1.  **Strict Separation**: UI files (`src/ui`) must NEVER contain business logic. They must call `src/services`.
2.  **Hardware Awareness**: All recommendations must be validated against `SystemService` constraints (VRAM, RAM).
3.  **Data Schemas**: Use `src/schemas` for data objects (EnvironmentReport, UserProfile) to avoid confusion with AI "models".
4.  **Async UI**: Long-running tasks (downloads, installs) must run in background threads to keep the UI responsive.

## Implementation Plan (V2.0)

### Phase 1: Critical Fixes (BLOCKER)
*   [ ] Fix `messagebox` import in `src/ui/views/comfyui.py`.
*   [ ] Fix Apple Silicon RAM detection in `src/services/system_service.py`.
*   [ ] Implement comprehensive hardware scanning (Storage, Form Factor).

### Phase 2: Core Services & Schemas
*   [ ] Create `src/schemas/` structure.
*   [ ] Implement `DownloadService` (Retry logic, Hashing).
*   [ ] Implement `ShortcutService` (Cross-platform).
*   [ ] Update `RecommendationService` to use weighted scoring.

### Phase 3: Setup Wizard UI
*   [ ] Create `src/ui/wizard/` structure.
*   [ ] Implement Experience & Use Case survey screens.
*   [ ] Implement Hardware Scan visualization.
*   [ ] Implement Installation Progress screen.

### Phase 4: ComfyUI Integration
*   [ ] Update `resources.json` with Wan 2.2 and GGUF models.
*   [ ] Implement `ComfyService.deploy_workflow`.
*   [ ] Add "Re-run Wizard" to Settings.

## Current Context
*   **OS**: Windows (win32)
*   **Shell**: PowerShell
*   **Virtual Env**: `.dashboard_env/venv` (Must use for all python commands)
*   **Status**: Phase 1 in progress.