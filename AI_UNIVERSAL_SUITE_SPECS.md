# AI Universal Suite - Technical Specification v2.0

## Executive Summary

AI Universal Suite is a cross-platform desktop application that transforms a user's computer into a fully configured AI workstation through a single, guided setup wizard. The application targets non-technical users who want to leverage AI tools without writing code, using terminals, or navigating complex installations.

**Core Principle:** The user should never need to open a terminal, write code, or understand technical implementation details. Every action should be achievable through GUI interactions.

---

## Table of Contents

1. [Strategic Vision](#1-strategic-vision)
2. [Architecture Overview](#2-architecture-overview)
3. [User Flow](#3-user-flow)
4. [Data Schemas](#4-data-schemas)
5. [Service Layer Specifications](#5-service-layer-specifications)
6. [UI Component Specifications](#6-ui-component-specifications)
7. [File Structure](#7-file-structure)
8. [Implementation Phases](#8-implementation-phases)
9. [Critical Bug Fixes](#9-critical-bug-fixes)
10. [Testing Requirements](#10-testing-requirements)

---

## 1. Strategic Vision

### 1.1 Problem Statement

Experienced professionals (filmmakers, designers, developers, business owners) understand that AI tools could transform their work, but face barriers:

- Consumer AI apps lack control and consistency
- Professional tools require coding knowledge
- Subscription costs accumulate without clear ROI
- No unified system ties tools together

### 1.2 Solution

AI Universal Suite provides:

1. **One-Shot Setup Wizard**: Fully configure an AI workstation in a single guided session
2. **Use-Case Driven Configuration**: Start from "what you want to accomplish" not "what software to install"
3. **Hardware-Aware Recommendations**: Automatically detect capabilities and recommend appropriate tools/models
4. **Zero Terminal Interaction**: All setup, configuration, and launching via GUI and desktop shortcuts
5. **Unified Tool Management**: Manage CLI tools, ComfyUI, API keys, and future modules from one interface

### 1.3 Target Users

| Persona | Description | Primary Use Cases |
|---------|-------------|-------------------|
| Creative Professional | Filmmakers, designers, photographers with domain expertise but limited technical skills | Image/video generation, content pipelines |
| Knowledge Worker | Business professionals, consultants, writers | AI assistants, document processing |
| Technical Veteran | Experienced developers/engineers learning AI tools | Full stack integration, automation |
| Solopreneur | Independent business owners wearing many hats | Productivity, content generation, automation |

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        UI Layer                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Setup Wizard│  │  Dashboard  │  │     Module Views        │  │
│  │  (Modal)    │  │  (Main)     │  │ (DevTools/ComfyUI/etc)  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ SetupWizard  │  │ Recommendation│  │    Module Services   │   │
│  │   Service    │  │    Service    │  │ (Comfy/CLI/Shortcut) │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   System     │  │   Download   │  │     Subprocess       │   │
│  │   Service    │  │    Service   │  │      Runner          │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Configuration Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ ConfigManager│  │ resources.json│  │    OS Keyring        │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Module System

The application is organized around **modules** - discrete functional units that can be independently configured, installed, and launched.

**Core Modules:**
| Module ID | Display Name | Description | Status |
|-----------|--------------|-------------|--------|
| `cli_provider` | AI Assistant CLI | Command-line AI with file system access | Implemented |
| `comfyui` | ComfyUI Studio | Visual AI generation (image/video) | Implemented |
| `lm_studio` | LM Studio | Local LLM inference | Planned |
| `mcp_servers` | MCP Configuration | Model Context Protocol servers | Planned |

### 2.3 Use Case System

Use cases sit above modules and define "what the user wants to accomplish." Each use case maps to a set of module configurations.

**Core Use Cases:**
| Use Case ID | Display Name | Modules Required |
|-------------|--------------|------------------|
| `content_generation` | Content Generation | comfyui, cli_provider (optional) |
| `video_generation` | Video Generation | comfyui (with I2V bundle) |
| `productivity` | AI Productivity | cli_provider |
| `automation` | Workflow Automation | cli_provider, mcp_servers |
| `full_stack` | Full AI Workstation | All modules |

---

## 3. User Flow

### 3.1 First Launch Flow

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
┌─────────────┐  ┌─────────────┐
│ Show Setup  │  │ Show Main   │
│   Wizard    │  │  Dashboard  │
└─────────────┘  └─────────────┘
```

### 3.2 Setup Wizard Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SETUP WIZARD STAGES                           │
└─────────────────────────────────────────────────────────────────┘

Stage 1: Welcome & Use Case Selection
├── Display: Welcome message, value proposition
├── Input: Use case selection (cards with icons)
│   ├── Content Generation (Image/Video)
│   ├── AI Productivity (Writing/Coding Assistant)
│   ├── Full AI Workstation (Everything)
│   └── Custom (Advanced users)
├── Action: [Continue]
└── Skip: Not available (required)

       │
       ▼

Stage 2: Environment Scan (Automatic)
├── Display: Scanning animation with progress
├── Detect:
│   ├── Operating System
│   ├── GPU Type (NVIDIA/Apple Silicon/CPU)
│   ├── VRAM (or unified memory for Apple)
│   ├── Available RAM
│   ├── Available Disk Space
│   ├── Existing installations (Node.js, Git, Python, ComfyUI)
│   └── Network connectivity
├── Output: EnvironmentReport object
├── Action: Automatic progression
└── Skip: Not available

       │
       ▼

Stage 3: Module Configuration Loop
├── For each module relevant to selected use case:
│   │
│   ├── Display:
│   │   ├── Module name and description
│   │   ├── Recommendation with reasoning
│   │   ├── Warnings (if any)
│   │   └── Configuration options (if applicable)
│   │
│   ├── Inputs (varies by module):
│   │   ├── CLI Provider: Provider selection, API key input
│   │   ├── ComfyUI: Model tier (auto-selected), optional features
│   │   └── Common: "Create desktop shortcut" checkbox
│   │
│   ├── Actions: [Skip] [Accept & Next]
│   └── Advanced: [Show Advanced Options] (reveals manual overrides)
│
└── Modules presented in order:
    1. CLI Provider (if applicable)
    2. ComfyUI (if applicable)
    3. LM Studio (if applicable, future)
    4. MCP Servers (if applicable, future)

       │
       ▼

Stage 4: Review & Confirm
├── Display:
│   ├── Summary of all accepted modules
│   ├── Total estimated download size
│   ├── Estimated installation time
│   ├── List of shortcuts to be created
│   └── Warnings summary
├── Actions: [Back] [Begin Installation]
└── Skip: Not available

       │
       ▼

Stage 5: Installation
├── Display:
│   ├── Overall progress bar
│   ├── Current task indicator
│   ├── Per-item progress bars
│   └── Log output (collapsible)
├── Process:
│   ├── Install dependencies (Git, Node.js if missing)
│   ├── Clone repositories
│   ├── Download models
│   ├── Configure environments
│   ├── Validate installations
│   └── Create shortcuts
├── Error Handling:
│   ├── Retry failed downloads (3 attempts, exponential backoff)
│   ├── Show clear error messages
│   └── Allow [Retry] or [Skip This Item]
└── Actions: [Cancel] (with confirmation)

       │
       ▼

Stage 6: Complete
├── Display:
│   ├── Success message
│   ├── List of installed tools with status
│   ├── List of created shortcuts
│   └── Quick start tips
├── Actions: [Open Dashboard] [Launch ComfyUI] [Close]
└── Side Effect: Set first_run = false in config
```

### 3.3 Post-Setup Dashboard Flow

After initial setup, the main dashboard provides:

1. **Overview Tab**: System status, installed modules, quick launch buttons
2. **Dev Tools Tab**: CLI management, API key updates
3. **ComfyUI Tab**: Model management, workflow templates, launch
4. **Settings Tab**: Preferences, re-run wizard, shortcuts management

---

## 4. Data Schemas

### 4.1 Configuration Schema (`config.json`)

```json
{
  "version": "2.0",
  "first_run": true,
  "wizard_completed": false,
  "theme": "Dark",
  "paths": {
    "comfyui": "~/ComfyUI",
    "lm_studio": "~/LMStudio",
    "shortcuts": "~/Desktop"
  },
  "modules": {
    "cli_provider": {
      "enabled": true,
      "provider": "claude",
      "shortcut_created": true
    },
    "comfyui": {
      "enabled": true,
      "use_case": "video_generation",
      "model_tier": "gguf",
      "shortcut_created": true
    }
  },
  "preferences": {
    "cli_scope": "user",
    "auto_update_check": true,
    "create_shortcuts": true
  }
}
```

### 4.2 Resources Schema (`resources.json`)

```json
{
  "version": "2.0",
  
  "use_cases": {
    "content_generation": {
      "display_name": "Content Generation",
      "description": "Generate images and graphics using AI",
      "icon": "🎨",
      "modules": ["comfyui"],
      "optional_modules": ["cli_provider"],
      "comfyui_config": {
        "capabilities": ["t2i", "i2i"],
        "recommended_features": ["controlnet", "ipadapter"]
      }
    },
    "video_generation": {
      "display_name": "Video Generation", 
      "description": "Animate images into video clips",
      "icon": "🎬",
      "modules": ["comfyui"],
      "optional_modules": ["cli_provider"],
      "comfyui_config": {
        "capabilities": ["i2v"],
        "required_nodes": ["ComfyUI-GGUF", "ComfyUI-VideoHelperSuite"],
        "required_models": ["wan_i2v"],
        "recommended_features": []
      }
    },
    "productivity": {
      "display_name": "AI Productivity",
      "description": "AI assistant for writing, coding, and analysis",
      "icon": "⚡",
      "modules": ["cli_provider"],
      "optional_modules": ["lm_studio"],
      "cli_config": {
        "recommended_provider": "claude"
      }
    },
    "full_stack": {
      "display_name": "Full AI Workstation",
      "description": "Complete setup with all AI tools",
      "icon": "🚀",
      "modules": ["cli_provider", "comfyui"],
      "optional_modules": ["lm_studio", "mcp_servers"],
      "comfyui_config": {
        "capabilities": ["t2i", "i2i", "i2v"],
        "recommended_features": ["controlnet", "ipadapter", "animatediff"]
      }
    }
  },

  "modules": {
    "cli_provider": {
      "display_name": "AI Assistant CLI",
      "description": "Command-line AI assistant with direct file system access. Enables AI-powered coding, writing, and file manipulation.",
      "requires_api_key": true,
      "providers": {
        "claude": {
          "display_name": "Claude (Anthropic)",
          "package": "@anthropic-ai/claude-code",
          "package_type": "npm",
          "bin": "claude",
          "api_key_name": "ANTHROPIC_API_KEY",
          "api_key_url": "https://console.anthropic.com/",
          "recommended_for": ["coding", "analysis", "writing"]
        },
        "gemini": {
          "display_name": "Gemini (Google)",
          "package": "@google/gemini-cli",
          "package_type": "npm",
          "bin": "gemini",
          "api_key_name": "GEMINI_API_KEY",
          "api_key_url": "https://aistudio.google.com/apikey",
          "recommended_for": ["research", "multimodal"]
        },
        "codex": {
          "display_name": "Codex (OpenAI)",
          "package": "@openai/codex",
          "package_type": "npm",
          "bin": "codex",
          "api_key_name": "OPENAI_API_KEY",
          "api_key_url": "https://platform.openai.com/api-keys",
          "recommended_for": ["coding"]
        }
      },
      "shortcut_templates": {
        "windows": "@echo off\ncmd /k {bin}",
        "darwin": "#!/bin/bash\n{bin}",
        "linux": "#!/bin/bash\n{bin}"
      }
    },
    
    "comfyui": {
      "display_name": "ComfyUI Studio",
      "description": "Visual node-based AI image and video generation. Create complex pipelines without coding.",
      "requires_api_key": false,
      "core": {
        "repo": "https://github.com/comfyanonymous/ComfyUI.git",
        "manager_repo": "https://github.com/ltdrdata/ComfyUI-Manager.git"
      },
      "shortcut_templates": {
        "windows": "@echo off\ncd /d {path}\ncall venv\\Scripts\\activate\npython main.py --auto-launch\npause",
        "darwin": "#!/bin/bash\ncd \"{path}\"\nsource venv/bin/activate\npython main.py --force-fp16 --auto-launch",
        "linux": "#!/bin/bash\ncd \"{path}\"\nsource venv/bin/activate\npython main.py --auto-launch"
      }
    },
    
    "lm_studio": {
      "display_name": "LM Studio",
      "description": "Run large language models locally on your machine.",
      "requires_api_key": false,
      "status": "planned",
      "download_urls": {
        "windows": "https://releases.lmstudio.ai/windows/latest",
        "darwin": "https://releases.lmstudio.ai/mac/latest",
        "linux": "https://releases.lmstudio.ai/linux/latest"
      }
    }
  },

  "comfyui_components": {
    "custom_nodes": {
      "ComfyUI-GGUF": {
        "display_name": "GGUF Model Loader",
        "description": "Load quantized GGUF models for reduced VRAM usage",
        "repo": "https://github.com/city96/ComfyUI-GGUF.git",
        "required_for": ["gguf_models"],
        "dest_folder": "custom_nodes/ComfyUI-GGUF"
      },
      "ComfyUI-VideoHelperSuite": {
        "display_name": "Video Helper Suite",
        "description": "Video loading, saving, and manipulation tools",
        "repo": "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git",
        "required_for": ["i2v", "video"],
        "dest_folder": "custom_nodes/ComfyUI-VideoHelperSuite"
      },
      "ComfyUI-AnimateDiff-Evolved": {
        "display_name": "AnimateDiff",
        "description": "Animation and motion generation",
        "repo": "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git",
        "required_for": ["animatediff"],
        "dest_folder": "custom_nodes/ComfyUI-AnimateDiff-Evolved"
      },
      "ComfyUI_IPAdapter_plus": {
        "display_name": "IP-Adapter Plus",
        "description": "Image-based style and character consistency",
        "repo": "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git",
        "required_for": ["ipadapter", "consistency"],
        "dest_folder": "custom_nodes/ComfyUI_IPAdapter_plus"
      },
      "comfyui_controlnet_aux": {
        "display_name": "ControlNet Preprocessors",
        "description": "Pose, depth, and edge detection for controlled generation",
        "repo": "https://github.com/Fannovel16/comfyui_controlnet_aux.git",
        "required_for": ["controlnet", "editing"],
        "dest_folder": "custom_nodes/comfyui_controlnet_aux"
      }
    },
    
    "model_tiers": {
      "flux": {
        "display_name": "Flux (High-End)",
        "min_vram": 12,
        "min_ram": 32,
        "description": "Highest quality, requires powerful GPU"
      },
      "sdxl": {
        "display_name": "SDXL (Standard)",
        "min_vram": 8,
        "min_ram": 16,
        "description": "Great quality, moderate requirements"
      },
      "sd15": {
        "display_name": "SD 1.5 (Lightweight)",
        "min_vram": 4,
        "min_ram": 8,
        "description": "Good quality, runs on most hardware"
      },
      "gguf": {
        "display_name": "GGUF Quantized",
        "min_vram": 0,
        "min_ram": 16,
        "description": "Optimized for Apple Silicon and low VRAM systems",
        "requires_nodes": ["ComfyUI-GGUF"]
      }
    },
    
    "models": {
      "checkpoints": {
        "flux_schnell": {
          "display_name": "Flux.1 Schnell",
          "tier": "flux",
          "url": "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/flux1-schnell.safetensors",
          "size_gb": 23.8,
          "dest": "models/checkpoints",
          "capabilities": ["t2i"]
        },
        "sdxl_juggernaut": {
          "display_name": "Juggernaut XL v9",
          "tier": "sdxl",
          "url": "https://civitai.com/api/download/models/240840",
          "size_gb": 6.5,
          "dest": "models/checkpoints",
          "capabilities": ["t2i", "i2i"]
        },
        "sd15_realistic": {
          "display_name": "Realistic Vision 6",
          "tier": "sd15",
          "url": "https://civitai.com/api/download/models/130072",
          "size_gb": 2.0,
          "dest": "models/checkpoints",
          "capabilities": ["t2i", "i2i"]
        }
      },
      "unet_gguf": {
        "wan_i2v_high_q5": {
          "display_name": "Wan 2.2 I2V High Noise (Q5)",
          "tier": "gguf",
          "url": "https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF/resolve/main/HighNoise/Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf",
          "size_gb": 9.8,
          "dest": "models/unet",
          "capabilities": ["i2v"],
          "pair_with": "wan_i2v_low_q5"
        },
        "wan_i2v_low_q5": {
          "display_name": "Wan 2.2 I2V Low Noise (Q5)",
          "tier": "gguf",
          "url": "https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF/resolve/main/LowNoise/Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf",
          "size_gb": 9.8,
          "dest": "models/unet",
          "capabilities": ["i2v"],
          "pair_with": "wan_i2v_high_q5"
        }
      }
    },
    
    "workflows": {
      "wan_i2v_basic": {
        "display_name": "Image to Video (Basic)",
        "description": "Animate a still image into a short video clip",
        "file": "workflows/wan_i2v_basic.json",
        "requires_models": ["wan_i2v_high_q5", "wan_i2v_low_q5"],
        "requires_nodes": ["ComfyUI-GGUF", "ComfyUI-VideoHelperSuite"],
        "capabilities": ["i2v"]
      },
      "sdxl_basic": {
        "display_name": "Text to Image (SDXL)",
        "description": "Generate images from text prompts",
        "file": "workflows/sdxl_basic.json",
        "requires_models": ["sdxl_juggernaut"],
        "requires_nodes": [],
        "capabilities": ["t2i"]
      }
    }
  },

  "hardware_profiles": {
    "nvidia_high": {
      "description": "NVIDIA GPU with 12GB+ VRAM",
      "detection": {"gpu_vendor": "nvidia", "vram_min": 12},
      "recommended_tier": "flux",
      "capabilities": ["cuda", "full_precision"]
    },
    "nvidia_mid": {
      "description": "NVIDIA GPU with 8-11GB VRAM",
      "detection": {"gpu_vendor": "nvidia", "vram_min": 8, "vram_max": 11},
      "recommended_tier": "sdxl",
      "capabilities": ["cuda", "full_precision"]
    },
    "nvidia_low": {
      "description": "NVIDIA GPU with 4-7GB VRAM",
      "detection": {"gpu_vendor": "nvidia", "vram_min": 4, "vram_max": 7},
      "recommended_tier": "sd15",
      "capabilities": ["cuda"]
    },
    "apple_silicon": {
      "description": "Apple M-series chip",
      "detection": {"gpu_vendor": "apple"},
      "recommended_tier": "gguf",
      "capabilities": ["mps", "unified_memory"],
      "notes": "Use GGUF models for best performance"
    },
    "cpu_only": {
      "description": "No dedicated GPU detected",
      "detection": {"gpu_vendor": "none"},
      "recommended_tier": "sd15",
      "capabilities": [],
      "warnings": ["Generation will be very slow without GPU acceleration"]
    }
  },

  "system_requirements": {
    "minimum": {
      "ram_gb": 8,
      "disk_gb": 20,
      "python": "3.10"
    },
    "recommended": {
      "ram_gb": 32,
      "disk_gb": 100,
      "python": "3.10"
    }
  }
}
```

### 4.3 Environment Report Schema

```python
@dataclass
class EnvironmentReport:
    """Output of SystemService.scan_full_environment()"""
    
    # Hardware
    os_name: str                    # "Windows", "Darwin", "Linux"
    os_version: str                 # e.g., "10.0.19041", "14.1.2"
    arch: str                       # "x86_64", "arm64"
    gpu_vendor: str                 # "nvidia", "apple", "amd", "none"
    gpu_name: str                   # "NVIDIA GeForce RTX 3080"
    vram_gb: int                    # 10
    ram_gb: int                     # 64
    disk_free_gb: int               # 250
    
    # Software
    python_version: str             # "3.10.12"
    git_installed: bool
    node_installed: bool
    npm_installed: bool
    
    # Existing Installations
    comfyui_path: Optional[str]     # None or path if found
    comfyui_version: Optional[str]
    lm_studio_installed: bool
    
    # Derived
    hardware_profile: str           # Key from hardware_profiles
    recommended_model_tier: str     # "flux", "sdxl", "sd15", "gguf"
    warnings: List[str]             # Any issues detected
```

### 4.4 Module Recommendation Schema

```python
@dataclass
class ModuleRecommendation:
    """Output of RecommendationService for a single module"""
    
    module_id: str                          # "comfyui"
    enabled: bool                           # Whether to install
    
    # Module-specific config
    config: Dict[str, Any]                  # Varies by module
    
    # For display
    display_name: str
    description: str
    reasoning: List[str]                    # Why this recommendation
    warnings: List[str]                     # Potential issues
    
    # Installation details
    components: List[str]                   # What will be installed
    estimated_size_gb: float
    estimated_time_minutes: int
    
    # User overridable
    optional_features: Dict[str, bool]      # Feature toggles
    advanced_options: Dict[str, Any]        # For advanced mode
```

### 4.5 Installation Manifest Schema

```python
@dataclass
class InstallationItem:
    """Single item to install"""
    
    item_id: str                    # Unique identifier
    item_type: str                  # "clone", "download", "pip", "npm", "shortcut"
    name: str                       # Display name
    
    # Type-specific fields
    url: Optional[str]              # For clone/download
    dest: str                       # Destination path
    command: Optional[List[str]]    # For pip/npm
    
    # Validation
    expected_hash: Optional[str]    # SHA256 for downloads
    verify_path: Optional[str]      # Path to check after install
    
    # Progress tracking
    size_bytes: Optional[int]
    
@dataclass  
class InstallationManifest:
    """Complete installation plan"""
    
    manifest_id: str                        # UUID
    created_at: datetime
    
    items: List[InstallationItem]
    
    # Summary
    total_size_gb: float
    estimated_time_minutes: int
    
    # Shortcuts to create after installation
    shortcuts: List[Dict[str, str]]         # {name, command, icon}
```

---

## 5. Service Layer Specifications

### 5.1 SystemService (Enhanced)

**File:** `src/services/system_service.py`

**Changes Required:**
- Fix Apple Silicon RAM detection (currently hardcoded to 16GB)
- Add full environment scanning method
- Add disk space checking

```python
class SystemService:
    
    @staticmethod
    def get_gpu_info() -> Tuple[str, str, int]:
        """
        Returns (gpu_vendor, gpu_name, vram_gb)
        
        MUST FIX: Apple Silicon currently hardcoded to 16GB.
        Should use: subprocess.check_output(["sysctl", "-n", "hw.memsize"])
        """
        pass
    
    @staticmethod
    def get_system_ram_gb() -> int:
        """Returns total system RAM in GB."""
        pass
    
    @staticmethod
    def get_disk_free_gb(path: str = "~") -> int:
        """Returns free disk space at path in GB."""
        pass
    
    @staticmethod
    def scan_full_environment() -> EnvironmentReport:
        """
        Comprehensive environment scan for wizard.
        Returns EnvironmentReport dataclass.
        """
        pass
    
    @staticmethod
    def detect_existing_comfyui() -> Optional[str]:
        """
        Check common locations for existing ComfyUI installation.
        Returns path if found, None otherwise.
        """
        pass
    
    @staticmethod
    def match_hardware_profile(env: EnvironmentReport) -> str:
        """
        Match environment to hardware_profiles in resources.json.
        Returns profile key.
        """
        pass
```

### 5.2 RecommendationService (Enhanced)

**File:** `src/services/recommendation_service.py`

**Changes Required:**
- Integrate with use case system
- Support GGUF model recommendations
- Add workflow template recommendations

```python
class RecommendationService:
    
    def __init__(self, resources: dict):
        self.resources = resources
    
    def generate_recommendations(
        self, 
        use_case: str, 
        env: EnvironmentReport
    ) -> List[ModuleRecommendation]:
        """
        Generate recommendations for all modules relevant to use case.
        
        Args:
            use_case: Key from resources["use_cases"]
            env: EnvironmentReport from SystemService
            
        Returns:
            List of ModuleRecommendation for each relevant module
        """
        pass
    
    def _recommend_cli_provider(
        self, 
        use_case_config: dict, 
        env: EnvironmentReport
    ) -> ModuleRecommendation:
        """Generate CLI provider recommendation."""
        pass
    
    def _recommend_comfyui(
        self, 
        use_case_config: dict, 
        env: EnvironmentReport
    ) -> ModuleRecommendation:
        """
        Generate ComfyUI recommendation including:
        - Model tier selection based on hardware
        - Required custom nodes for capabilities
        - Workflow templates
        - GGUF models for Apple Silicon
        """
        pass
    
    def _select_model_tier(self, env: EnvironmentReport) -> str:
        """
        Select appropriate model tier based on hardware.
        Apple Silicon should default to "gguf".
        """
        pass
    
    def _get_required_components(
        self, 
        capabilities: List[str], 
        model_tier: str
    ) -> Dict[str, List[str]]:
        """
        Given required capabilities and tier, return:
        {
            "custom_nodes": [...],
            "models": [...],
            "workflows": [...]
        }
        """
        pass
```

### 5.3 SetupWizardService (New)

**File:** `src/services/setup_wizard_service.py`

```python
class SetupWizardService:
    """
    Orchestrates the full setup wizard flow.
    Coordinates between SystemService, RecommendationService, 
    and module-specific services.
    """
    
    def __init__(self):
        self.system_service = SystemService()
        self.recommendation_service = RecommendationService(
            config_manager.get_resources()
        )
        self.env_report: Optional[EnvironmentReport] = None
        self.recommendations: List[ModuleRecommendation] = []
        self.accepted_modules: List[ModuleRecommendation] = []
    
    def start_wizard(self) -> None:
        """Initialize wizard state."""
        self.env_report = None
        self.recommendations = []
        self.accepted_modules = []
    
    def scan_environment(self) -> EnvironmentReport:
        """
        Run full environment scan.
        Stores result in self.env_report.
        """
        self.env_report = self.system_service.scan_full_environment()
        return self.env_report
    
    def generate_recommendations(self, use_case: str) -> List[ModuleRecommendation]:
        """
        Generate recommendations for selected use case.
        Requires scan_environment() to have been called first.
        """
        if not self.env_report:
            raise RuntimeError("Must scan environment first")
        
        self.recommendations = self.recommendation_service.generate_recommendations(
            use_case, self.env_report
        )
        return self.recommendations
    
    def accept_module(self, module_id: str, config_overrides: Dict = None) -> None:
        """Mark a module as accepted, optionally with config changes."""
        pass
    
    def skip_module(self, module_id: str) -> None:
        """Mark a module as skipped."""
        pass
    
    def generate_manifest(self) -> InstallationManifest:
        """
        Generate unified installation manifest from accepted modules.
        """
        pass
    
    def execute_installation(
        self, 
        manifest: InstallationManifest,
        progress_callback: Callable[[str, float], None],
        error_callback: Callable[[str, Exception], None]
    ) -> bool:
        """
        Execute the installation manifest.
        
        Args:
            manifest: What to install
            progress_callback: Called with (item_id, progress 0-1)
            error_callback: Called with (item_id, exception)
            
        Returns:
            True if all items succeeded, False if any failed
        """
        pass
    
    def create_shortcuts(self) -> List[Path]:
        """Create desktop shortcuts for installed tools."""
        pass
    
    def finalize(self) -> None:
        """
        Mark wizard as complete.
        Updates config with wizard_completed=True and first_run=False.
        """
        pass
```

### 5.4 ShortcutService (New)

**File:** `src/services/shortcut_service.py`

```python
class ShortcutService:
    """
    Creates OS-appropriate desktop shortcuts/launchers.
    """
    
    @staticmethod
    def get_desktop_path() -> Path:
        """Returns path to user's Desktop folder."""
        pass
    
    @staticmethod
    def create_shortcut(
        name: str,
        command: str,
        working_dir: Optional[str] = None,
        icon_path: Optional[str] = None,
        destination: Optional[Path] = None
    ) -> Path:
        """
        Create a desktop shortcut.
        
        Windows: Creates .bat file
        macOS: Creates .command file, removes quarantine attribute
        Linux: Creates .desktop file or .sh script
        
        Args:
            name: Display name (also used for filename)
            command: Command to execute
            working_dir: Working directory for command
            icon_path: Path to icon file (optional)
            destination: Where to create (default: Desktop)
            
        Returns:
            Path to created shortcut
        """
        pass
    
    @staticmethod
    def create_comfyui_shortcut(comfy_path: str) -> Path:
        """Create ComfyUI launcher shortcut."""
        pass
    
    @staticmethod
    def create_cli_shortcut(cli_name: str, bin_name: str) -> Path:
        """Create CLI tool launcher shortcut."""
        pass
    
    @staticmethod
    def remove_macos_quarantine(path: Path) -> None:
        """Remove macOS quarantine attribute to prevent security warnings."""
        pass
```

### 5.5 DownloadService (New)

**File:** `src/services/download_service.py`

```python
class DownloadService:
    """
    Handles file downloads with progress tracking, retry logic, and validation.
    """
    
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2  # Exponential backoff base
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks
    
    @staticmethod
    def download_file(
        url: str,
        dest_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        expected_hash: Optional[str] = None
    ) -> bool:
        """
        Download a file with retry logic.
        
        Args:
            url: Source URL
            dest_path: Destination file path
            progress_callback: Called with (bytes_downloaded, total_bytes)
            expected_hash: SHA256 hash to verify (optional)
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            DownloadError: If all retries fail
            HashMismatchError: If hash doesn't match
        """
        pass
    
    @staticmethod
    def verify_hash(file_path: Path, expected_hash: str) -> bool:
        """Verify file SHA256 hash."""
        pass
    
    @staticmethod
    def get_file_size(url: str) -> Optional[int]:
        """Get file size from URL headers without downloading."""
        pass
```

### 5.6 ComfyService (Enhanced)

**File:** `src/services/comfy_service.py`

**Changes Required:**
- Accept ModuleRecommendation as input instead of raw answers
- Support GGUF model installation
- Support workflow template deployment
- Add update and validation methods

```python
class ComfyService:
    
    @staticmethod
    def generate_manifest(
        recommendation: ModuleRecommendation,
        install_path: str
    ) -> List[InstallationItem]:
        """
        Generate installation items from recommendation.
        
        Now supports:
        - GGUF custom node and models
        - Workflow template copying
        - All model tiers
        """
        pass
    
    @staticmethod
    def install_custom_node(node_url: str, dest_path: str) -> bool:
        """Clone a custom node repository."""
        pass
    
    @staticmethod
    def deploy_workflow(
        workflow_key: str, 
        comfy_path: str,
        resources: dict
    ) -> bool:
        """
        Copy workflow template to ComfyUI workflows directory.
        
        Source: bundled workflows/ directory in app
        Dest: {comfy_path}/user/default/workflows/
        """
        pass
    
    @staticmethod
    def validate_installation(comfy_path: str) -> Dict[str, bool]:
        """
        Validate ComfyUI installation.
        
        Returns dict of checks:
        {
            "core_exists": bool,
            "venv_exists": bool,
            "manager_exists": bool,
            "can_launch": bool
        }
        """
        pass
    
    @staticmethod
    def get_installed_models(comfy_path: str) -> Dict[str, List[str]]:
        """
        List installed models by category.
        
        Returns:
        {
            "checkpoints": ["model1.safetensors", ...],
            "unet": ["wan_i2v_high.gguf", ...],
            "loras": [...]
        }
        """
        pass
```

### 5.7 DevService (Enhanced)

**File:** `src/services/dev_service.py`

**Changes Required:**
- Add uninstall method
- Add method to check API key validity
- Integrate with shortcut creation

```python
class DevService:
    
    @staticmethod
    def get_install_cmd(tool_name: str, scope: str = "user") -> List[str]:
        """Get installation command for a CLI tool."""
        pass
    
    @staticmethod
    def get_uninstall_cmd(tool_name: str, scope: str = "user") -> List[str]:
        """
        Get uninstall command for a CLI tool.
        
        npm: ["npm", "uninstall", "-g", package]
        pip: [sys.executable, "-m", "pip", "uninstall", "-y", package]
        """
        pass
    
    @staticmethod
    def validate_api_key(provider: str, api_key: str) -> bool:
        """
        Validate an API key by making a minimal API call.
        
        Returns True if key is valid, False otherwise.
        """
        pass
    
    @staticmethod
    def get_binary_path(tool_name: str) -> Optional[str]:
        """Get full path to installed CLI binary."""
        pass
```

---

## 6. UI Component Specifications

### 6.1 Setup Wizard Window

**File:** `src/ui/wizard/setup_wizard.py`

```python
class SetupWizard(ctk.CTkToplevel):
    """
    Modal wizard window for initial setup.
    Manages multi-stage flow with back/next navigation.
    """
    
    def __init__(self, master, on_complete: Callable):
        """
        Args:
            master: Parent window
            on_complete: Callback when wizard finishes
        """
        pass
    
    # Stage management
    def show_stage(self, stage_name: str) -> None:
        """Switch to a wizard stage."""
        pass
    
    def next_stage(self) -> None:
        """Advance to next stage."""
        pass
    
    def prev_stage(self) -> None:
        """Go back to previous stage."""
        pass
    
    # Stages (each implemented as a method that builds the UI)
    def build_welcome_stage(self) -> ctk.CTkFrame:
        """Use case selection cards."""
        pass
    
    def build_scanning_stage(self) -> ctk.CTkFrame:
        """Environment scan with progress."""
        pass
    
    def build_module_stage(self, module: ModuleRecommendation) -> ctk.CTkFrame:
        """
        Module configuration stage.
        Shows recommendation, reasoning, config options.
        """
        pass
    
    def build_review_stage(self) -> ctk.CTkFrame:
        """Final review before installation."""
        pass
    
    def build_installation_stage(self) -> ctk.CTkFrame:
        """Installation progress display."""
        pass
    
    def build_complete_stage(self) -> ctk.CTkFrame:
        """Success screen with next steps."""
        pass
```

### 6.2 Wizard Stage Components

**File:** `src/ui/wizard/components/`

```
components/
├── use_case_card.py      # Clickable card for use case selection
├── module_config.py      # Module configuration panel
├── api_key_input.py      # API key entry with validation
├── progress_panel.py     # Installation progress display
├── reasoning_display.py  # Shows recommendation reasoning
└── warning_banner.py     # Warning/error display
```

### 6.3 App Modifications

**File:** `src/ui/app.py`

**Changes Required:**
- Check `wizard_completed` flag on startup
- Show wizard modal if needed
- Add method to re-run wizard from settings

```python
class App(ctk.CTk):
    def __init__(self):
        # ... existing init ...
        
        # Check if wizard needed
        if not config_manager.get("wizard_completed", False):
            self.after(100, self.show_setup_wizard)
    
    def show_setup_wizard(self):
        """Launch the setup wizard."""
        wizard = SetupWizard(self, on_complete=self.on_wizard_complete)
        wizard.grab_set()  # Make modal
    
    def on_wizard_complete(self):
        """Called when wizard finishes."""
        # Refresh all views to reflect new installations
        self.refresh_all_views()
```

---

## 7. File Structure

### 7.1 New Files to Create

```
src/
├── services/
│   ├── setup_wizard_service.py    # NEW: Wizard orchestration
│   ├── shortcut_service.py        # NEW: Desktop shortcut creation
│   ├── download_service.py        # NEW: Download with retry/progress
│   └── recommendation_service.py  # EXISTS: Enhance
│
├── ui/
│   ├── wizard/
│   │   ├── __init__.py
│   │   ├── setup_wizard.py        # NEW: Main wizard window
│   │   └── components/
│   │       ├── __init__.py
│   │       ├── use_case_card.py   # NEW
│   │       ├── module_config.py   # NEW
│   │       ├── api_key_input.py   # NEW
│   │       ├── progress_panel.py  # NEW
│   │       ├── reasoning_display.py # NEW
│   │       └── warning_banner.py  # NEW
│   │
│   └── views/
│       └── comfyui.py             # EXISTS: Update to use recommendations
│
├── config/
│   └── resources.json             # EXISTS: Major update per schema
│
└── workflows/                      # NEW: Bundled workflow templates
    ├── wan_i2v_basic.json
    ├── sdxl_basic.json
    └── README.md
```

### 7.2 Files to Modify

| File | Changes |
|------|---------|
| `src/services/system_service.py` | Fix Apple Silicon RAM, add full scan |
| `src/services/comfy_service.py` | Support GGUF, workflows, recommendations |
| `src/services/dev_service.py` | Add uninstall, API validation |
| `src/config/manager.py` | Add wizard_completed flag handling |
| `src/config/resources.json` | Complete rewrite per schema |
| `src/ui/app.py` | Add wizard launch logic |
| `src/ui/views/comfyui.py` | Fix messagebox import, use recommendations |
| `src/ui/views/settings.py` | Add "Re-run Setup Wizard" button |

---

## 8. Implementation Phases

### Phase 1: Critical Fixes (Do First)

**Priority: BLOCKER - App crashes without these**

1. Fix messagebox import in `src/ui/views/comfyui.py`
   ```python
   from tkinter import filedialog, ttk, messagebox
   ```

2. Fix Apple Silicon RAM detection in `src/services/system_service.py`
   ```python
   elif platform.system() == "Darwin" and platform.machine() == "arm64":
       gpu_name = "Apple Silicon (MPS)"
       try:
           result = subprocess.check_output(["sysctl", "-n", "hw.memsize"])
           ram_bytes = int(result.strip())
           vram_gb = ram_bytes // (1024**3)  # Unified memory = RAM
       except:
           vram_gb = 16  # Fallback
   ```

### Phase 2: GGUF & Video Support

**Priority: HIGH - Enables Andy use case**

1. Add to `resources.json`:
   - ComfyUI-GGUF custom node definition
   - Wan 2.2 I2V GGUF model definitions
   - Video generation use case

2. Update `ComfyService.generate_manifest()` to handle GGUF models

3. Create `workflows/wan_i2v_basic.json` template

4. Add workflow deployment logic

### Phase 3: Core Services

**Priority: HIGH - Foundation for wizard**

1. Create `ShortcutService`
2. Create `DownloadService` 
3. Enhance `SystemService` with full environment scan
4. Create `SetupWizardService`

### Phase 4: Wizard UI

**Priority: HIGH - User-facing feature**

1. Create wizard window skeleton
2. Implement use case selection stage
3. Implement environment scan stage
4. Implement module configuration stages
5. Implement review stage
6. Implement installation stage
7. Implement completion stage

### Phase 5: Integration & Polish

**Priority: MEDIUM**

1. Connect wizard to app startup
2. Add "Re-run Wizard" to settings
3. Update existing views to reflect wizard choices
4. Add API key validation
5. Comprehensive error handling
6. User testing and refinement

### Phase 6: Future Modules

**Priority: LOW - After core is stable**

1. LM Studio module
2. MCP configuration module
3. Advanced mode features

---

## 9. Critical Bug Fixes

### 9.1 Messagebox Import (BLOCKER)

**File:** `src/ui/views/comfyui.py`

**Current (Broken):**
```python
from tkinter import filedialog, ttk
```

**Fixed:**
```python
from tkinter import filedialog, ttk, messagebox
```

### 9.2 Apple Silicon RAM Detection (HIGH)

**File:** `src/services/system_service.py`

**Current (Broken):**
```python
elif platform.system() == "Darwin" and platform.machine() == "arm64":
    gpu_name = "Apple Silicon (MPS)"
    vram_gb = 16  # Hardcoded - WRONG
```

**Fixed:**
```python
elif platform.system() == "Darwin" and platform.machine() == "arm64":
    gpu_name = "Apple Silicon (MPS)"
    try:
        # Get actual unified memory
        result = subprocess.check_output(
            ["sysctl", "-n", "hw.memsize"],
            creationflags=0  # No Windows flags on Mac
        )
        ram_bytes = int(result.strip())
        vram_gb = ram_bytes // (1024**3)
    except Exception as e:
        log.warning(f"Could not detect Mac RAM: {e}")
        vram_gb = 16  # Conservative fallback
```

---

## 10. Testing Requirements

### 10.1 Unit Tests

| Service | Test Cases |
|---------|------------|
| SystemService | GPU detection (NVIDIA, Apple, none), RAM detection, disk space |
| RecommendationService | Each use case + hardware combination |
| ShortcutService | Shortcut creation on each OS |
| DownloadService | Success, retry on failure, hash validation |
| SetupWizardService | Full flow, skip handling, error recovery |

### 10.2 Integration Tests

1. Full wizard flow on Windows with NVIDIA GPU
2. Full wizard flow on macOS with Apple Silicon
3. Full wizard flow on Linux
4. ComfyUI installation and launch
5. CLI tool installation and shortcut creation
6. API key storage and retrieval

### 10.3 Manual Testing Checklist

- [ ] First launch shows wizard
- [ ] Environment scan completes without errors
- [ ] Recommendations make sense for hardware
- [ ] Skip button works on each module
- [ ] API key input and validation works
- [ ] Installation progress displays correctly
- [ ] Shortcuts are created and work
- [ ] ComfyUI launches successfully
- [ ] CLI tools launch from shortcuts
- [ ] Re-run wizard from settings works
- [ ] App remembers wizard_completed state

---

## Appendix A: Consulting Proposal Alignment

This specification directly supports the AI Infrastructure Consulting proposal:

| Proposal Deliverable | App Feature |
|---------------------|-------------|
| **Quick Win Session** | Setup wizard completes full stack in one session |
| **Full Stack Audit** | Environment scan + reasoning display |
| **ComfyUI Pipelines** | Workflow template deployment |
| **CLI/API Setup** | CLI provider module with API key management |
| **Cost Optimization** | CLI tools use pay-per-use API, not subscriptions |
| **Desktop Shortcuts** | ShortcutService creates launchers |
| **No Coding Required** | Entire flow is GUI-based |

---

## Appendix B: Video Generation Use Case (Andy)

Specific requirements for the documentary filmmaker use case:

**Input:** Historical photograph + audio track
**Output:** 5-10 second animated video clip

**Required Components:**
1. ComfyUI-GGUF node (for Apple Silicon compatibility)
2. Wan 2.2 I2V High Noise GGUF model
3. Wan 2.2 I2V Low Noise GGUF model
4. Video Helper Suite node
5. wan_i2v_basic.json workflow template

**Hardware Profile:** Apple Silicon with 64GB unified memory
**Recommended Tier:** GGUF (not full precision)

**Workflow Template Contents:**
- Two Unet Loader (GGUF) nodes configured for High/Low noise models
- Load Image node
- WanImageToVideo node
- Video output node
- Preset resolution: 320x320 (for testing), 640x640 (for production)

---

## 11. Model Management System

### 11.1 Overview

Post-installation model management allowing users to browse, download, organize, and remove models without touching the file system directly.

**Core Capabilities:**
- Browse installed models by category (checkpoints, loras, unet, vae, controlnet, etc.)
- Download new models from curated repositories (HuggingFace, CivitAI)
- Hash verification for security and integrity
- Move/copy models between directories
- Batch operations (select multiple, delete, move)
- Model metadata display (size, hash, source, capabilities)

### 11.2 Model Directory Structure

ComfyUI uses this standard structure under `{comfy_path}/models/`:

```
models/
├── checkpoints/        # Main generation models (.safetensors, .ckpt)
├── clip/               # Text encoders
├── clip_vision/        # Vision encoders
├── controlnet/         # ControlNet models
├── embeddings/         # Textual inversions
├── loras/              # LoRA fine-tunes
├── style_models/       # Style transfer models
├── unet/               # GGUF and standalone UNet models
├── upscale_models/     # Upscaling models
└── vae/                # VAE models
```

### 11.3 Data Schemas

#### Model Registry Entry

```python
@dataclass
class LocalModel:
    """Represents an installed model file."""
    
    filename: str                       # "juggernaut_xl_v9.safetensors"
    filepath: Path                      # Full path
    category: str                       # "checkpoints", "loras", etc.
    size_bytes: int
    hash_sha256: Optional[str]          # Computed on demand, cached
    
    # Metadata (if known)
    display_name: Optional[str]         # "Juggernaut XL v9"
    source_url: Optional[str]           # Where it was downloaded from
    source_repo: Optional[str]          # "civitai", "huggingface"
    model_type: Optional[str]           # "sdxl", "sd15", "flux", "gguf"
    capabilities: List[str]             # ["t2i", "i2i"]
    
    # Status
    verified: bool                      # Hash matches known good value
    created_at: datetime
    last_used: Optional[datetime]
```

#### Repository Model Entry

```python
@dataclass
class RepoModel:
    """Represents a model available for download from a repository."""
    
    repo_id: str                        # Unique ID in the repo
    repo_source: str                    # "huggingface", "civitai"
    
    display_name: str
    description: str
    author: str
    
    # Files available
    files: List[RepoModelFile]
    
    # Metadata
    model_type: str                     # "sdxl", "sd15", "flux", "gguf"
    base_model: Optional[str]           # What it's based on
    capabilities: List[str]
    tags: List[str]
    
    # Stats
    downloads: int
    rating: Optional[float]
    
    # Safety
    nsfw: bool
    verified_safe: bool                 # Has been scanned/reviewed
    
@dataclass
class RepoModelFile:
    """Single downloadable file within a repo model."""
    
    filename: str
    url: str
    size_bytes: int
    hash_sha256: Optional[str]
    quantization: Optional[str]         # "Q5_K_M", "Q8", "fp16", "fp32"
    format: str                         # "safetensors", "gguf", "ckpt"
```

### 11.4 ModelManagerService

**File:** `src/services/model_manager_service.py`

```python
class ModelManagerService:
    """
    Manages local model files in ComfyUI installation.
    """
    
    SUPPORTED_EXTENSIONS = [".safetensors", ".ckpt", ".pt", ".pth", ".gguf", ".bin"]
    
    def __init__(self, comfy_path: str):
        self.comfy_path = Path(comfy_path)
        self.models_path = self.comfy_path / "models"
        self._hash_cache: Dict[str, str] = {}  # filepath -> hash
    
    # === Browsing ===
    
    def get_categories(self) -> List[str]:
        """
        List all model subdirectories.
        Returns: ["checkpoints", "loras", "unet", ...]
        """
        pass
    
    def list_models(self, category: str) -> List[LocalModel]:
        """
        List all models in a category.
        
        Args:
            category: Subdirectory name (e.g., "checkpoints")
            
        Returns:
            List of LocalModel objects
        """
        pass
    
    def list_all_models(self) -> Dict[str, List[LocalModel]]:
        """
        List all models across all categories.
        
        Returns:
            Dict mapping category -> list of models
        """
        pass
    
    def get_model_info(self, filepath: Path) -> LocalModel:
        """Get detailed info for a specific model file."""
        pass
    
    def search_models(self, query: str) -> List[LocalModel]:
        """Search models by filename or display name."""
        pass
    
    # === Hash Verification ===
    
    def compute_hash(self, filepath: Path) -> str:
        """
        Compute SHA256 hash of a model file.
        Uses chunked reading for large files.
        Caches result.
        """
        pass
    
    def verify_model(self, filepath: Path, expected_hash: str) -> bool:
        """Verify model file matches expected hash."""
        pass
    
    def verify_all_models(
        self, 
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, bool]:
        """
        Verify all known models against stored hashes.
        
        Args:
            progress_callback: Called with (filename, current, total)
            
        Returns:
            Dict mapping filepath -> verification result
        """
        pass
    
    # === File Operations ===
    
    def delete_model(self, filepath: Path) -> bool:
        """
        Delete a model file.
        
        Returns:
            True if deleted, False if failed
        """
        pass
    
    def delete_models_batch(self, filepaths: List[Path]) -> Dict[str, bool]:
        """
        Delete multiple models.
        
        Returns:
            Dict mapping filepath -> success
        """
        pass
    
    def move_model(self, filepath: Path, dest_category: str) -> Path:
        """
        Move a model to a different category.
        
        Args:
            filepath: Current path
            dest_category: Target category (e.g., "loras")
            
        Returns:
            New filepath
        """
        pass
    
    def move_models_batch(
        self, 
        filepaths: List[Path], 
        dest_category: str
    ) -> Dict[str, Path]:
        """
        Move multiple models to a category.
        
        Returns:
            Dict mapping old path -> new path
        """
        pass
    
    def copy_model(self, filepath: Path, dest_category: str) -> Path:
        """Copy a model to a different category."""
        pass
    
    def rename_model(self, filepath: Path, new_name: str) -> Path:
        """
        Rename a model file.
        
        Args:
            filepath: Current path
            new_name: New filename (with extension)
            
        Returns:
            New filepath
        """
        pass
    
    # === Metadata ===
    
    def save_model_metadata(self, filepath: Path, metadata: dict) -> None:
        """
        Save metadata for a model to sidecar JSON file.
        Creates {filename}.meta.json alongside the model.
        """
        pass
    
    def load_model_metadata(self, filepath: Path) -> Optional[dict]:
        """Load metadata from sidecar file if exists."""
        pass
    
    # === Statistics ===
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        
        Returns:
            {
                "total_size_gb": float,
                "by_category": {"checkpoints": float, ...},
                "model_count": int,
                "largest_models": List[Tuple[str, float]]
            }
        """
        pass
```

### 11.5 ModelRepositoryService

**File:** `src/services/model_repository_service.py`

```python
class ModelRepositoryService:
    """
    Interface with external model repositories (HuggingFace, CivitAI).
    Provides browsing, search, and download capabilities.
    """
    
    def __init__(self):
        self.sources = {
            "huggingface": HuggingFaceAdapter(),
            "civitai": CivitAIAdapter()
        }
        self._curated_models: Optional[dict] = None  # Loaded from resources.json
    
    # === Curated Models ===
    
    def get_curated_models(
        self, 
        category: Optional[str] = None,
        model_type: Optional[str] = None,
        capabilities: Optional[List[str]] = None
    ) -> List[RepoModel]:
        """
        Get pre-vetted models from our curated list in resources.json.
        These are safe, tested, and have verified hashes.
        
        Args:
            category: Filter by category (checkpoints, loras, etc.)
            model_type: Filter by type (sdxl, sd15, flux, gguf)
            capabilities: Filter by capabilities (t2i, i2i, i2v)
            
        Returns:
            List of curated RepoModel entries
        """
        pass
    
    def get_recommended_models(
        self, 
        use_case: str, 
        hardware_profile: str
    ) -> List[RepoModel]:
        """
        Get models recommended for a specific use case and hardware.
        
        Args:
            use_case: From use_cases in resources.json
            hardware_profile: From hardware_profiles
            
        Returns:
            Sorted list of recommended models
        """
        pass
    
    # === Repository Search ===
    
    def search_huggingface(
        self,
        query: str,
        model_type: Optional[str] = None,
        limit: int = 20
    ) -> List[RepoModel]:
        """
        Search HuggingFace for models.
        
        Filters to ComfyUI-compatible formats.
        """
        pass
    
    def search_civitai(
        self,
        query: str,
        model_type: Optional[str] = None,
        nsfw: bool = False,
        limit: int = 20
    ) -> List[RepoModel]:
        """
        Search CivitAI for models.
        
        Args:
            query: Search query
            model_type: Filter by type
            nsfw: Include NSFW models
            limit: Max results
        """
        pass
    
    def search_all(
        self,
        query: str,
        **filters
    ) -> Dict[str, List[RepoModel]]:
        """
        Search all repositories.
        
        Returns:
            Dict mapping source -> results
        """
        pass
    
    # === Model Details ===
    
    def get_model_details(self, repo_source: str, repo_id: str) -> RepoModel:
        """Get full details for a specific model."""
        pass
    
    def get_available_files(self, repo_source: str, repo_id: str) -> List[RepoModelFile]:
        """
        Get all downloadable files for a model.
        
        Includes different quantizations, formats, etc.
        """
        pass
    
    # === Download ===
    
    def download_model(
        self,
        file: RepoModelFile,
        dest_category: str,
        comfy_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> LocalModel:
        """
        Download a model file to the appropriate directory.
        
        Args:
            file: RepoModelFile to download
            dest_category: Target category (checkpoints, loras, etc.)
            comfy_path: ComfyUI installation path
            progress_callback: Called with (bytes_downloaded, total_bytes)
            
        Returns:
            LocalModel representing the downloaded file
            
        Raises:
            HashMismatchError: If hash verification fails
            DownloadError: If download fails
        """
        pass
    
    def download_model_batch(
        self,
        files: List[Tuple[RepoModelFile, str]],  # (file, dest_category)
        comfy_path: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[LocalModel]:
        """
        Download multiple models.
        
        Args:
            files: List of (file, destination_category) tuples
            comfy_path: ComfyUI installation path
            progress_callback: Called with (filename, bytes_downloaded, total_bytes)
        """
        pass


class HuggingFaceAdapter:
    """Adapter for HuggingFace Hub API."""
    
    BASE_URL = "https://huggingface.co"
    API_URL = "https://huggingface.co/api"
    
    def search(self, query: str, **filters) -> List[dict]:
        """Search HuggingFace models."""
        pass
    
    def get_model_info(self, model_id: str) -> dict:
        """Get model metadata."""
        pass
    
    def get_file_url(self, model_id: str, filename: str) -> str:
        """Get direct download URL for a file."""
        pass


class CivitAIAdapter:
    """Adapter for CivitAI API."""
    
    BASE_URL = "https://civitai.com"
    API_URL = "https://civitai.com/api/v1"
    
    def search(self, query: str, **filters) -> List[dict]:
        """Search CivitAI models."""
        pass
    
    def get_model_info(self, model_id: str) -> dict:
        """Get model metadata."""
        pass
    
    def get_model_version(self, version_id: str) -> dict:
        """Get specific version details."""
        pass
    
    def get_download_url(self, version_id: str) -> str:
        """Get download URL (may require API key for some models)."""
        pass
```

### 11.6 Curated Models Schema (Addition to resources.json)

```json
{
  "model_repository": {
    "curated_models": {
      "checkpoints": [
        {
          "id": "juggernaut_xl_v9",
          "display_name": "Juggernaut XL v9",
          "description": "Photorealistic SDXL model, excellent for portraits and scenes",
          "source": "civitai",
          "source_id": "133005",
          "files": [
            {
              "filename": "juggernautXL_v9Rdphoto2Lightning.safetensors",
              "url": "https://civitai.com/api/download/models/240840",
              "size_bytes": 6938078792,
              "hash_sha256": "aeb7c9a6a0...",
              "format": "safetensors",
              "quantization": null
            }
          ],
          "model_type": "sdxl",
          "capabilities": ["t2i", "i2i"],
          "tags": ["photorealistic", "portrait", "landscape"],
          "min_vram": 8,
          "recommended_for": ["content_generation", "full_stack"]
        }
      ],
      "unet_gguf": [
        {
          "id": "wan_i2v_q5",
          "display_name": "Wan 2.2 Image-to-Video (Q5)",
          "description": "Quantized I2V model optimized for Apple Silicon and low VRAM",
          "source": "huggingface",
          "source_id": "QuantStack/Wan2.2-I2V-A14B-GGUF",
          "files": [
            {
              "filename": "Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf",
              "url": "https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF/resolve/main/HighNoise/Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf",
              "size_bytes": 10523648000,
              "hash_sha256": "abc123...",
              "format": "gguf",
              "quantization": "Q5_K_M"
            },
            {
              "filename": "Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf",
              "url": "https://huggingface.co/QuantStack/Wan2.2-I2V-A14B-GGUF/resolve/main/LowNoise/Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf",
              "size_bytes": 10523648000,
              "hash_sha256": "def456...",
              "format": "gguf",
              "quantization": "Q5_K_M"
            }
          ],
          "model_type": "gguf",
          "capabilities": ["i2v"],
          "tags": ["video", "animation", "apple-silicon"],
          "min_vram": 0,
          "min_ram": 32,
          "recommended_for": ["video_generation"],
          "requires_nodes": ["ComfyUI-GGUF"]
        }
      ],
      "loras": [],
      "controlnet": [],
      "vae": []
    },
    
    "trusted_sources": {
      "huggingface": {
        "display_name": "Hugging Face",
        "base_url": "https://huggingface.co",
        "api_url": "https://huggingface.co/api",
        "requires_auth": false,
        "safety_rating": "high"
      },
      "civitai": {
        "display_name": "CivitAI",
        "base_url": "https://civitai.com",
        "api_url": "https://civitai.com/api/v1",
        "requires_auth": false,
        "safety_rating": "medium",
        "notes": "User-uploaded content, verify hashes"
      }
    },
    
    "blocked_hashes": [
      "known_malicious_hash_1",
      "known_malicious_hash_2"
    ]
  }
}
```

### 11.7 Model Manager UI

**File:** `src/ui/views/model_manager.py`

```python
class ModelManagerFrame(ctk.CTkFrame):
    """
    Model management interface.
    
    Layout:
    ┌─────────────────────────────────────────────────────────────┐
    │ [Installed] [Browse & Download]                    [Search] │
    ├─────────────────────────────────────────────────────────────┤
    │ Categories │  Model List                          │ Details │
    │ ─────────  │  ──────────                          │ ─────── │
    │ checkpoints│  □ juggernaut_xl_v9.safetensors 6.5GB│ Name    │
    │ loras      │  □ realistic_vision.safetensors 2.0GB│ Size    │
    │ unet       │  ☑ wan_i2v_high.gguf          9.8GB  │ Hash    │
    │ vae        │                                      │ Source  │
    │ controlnet │                                      │         │
    │            │                                      │ [Verify]│
    ├────────────┴──────────────────────────────────────┴─────────┤
    │ Selected: 1 | [Move To...] [Copy To...] [Delete] | 16.3 GB  │
    └─────────────────────────────────────────────────────────────┘
    """
    
    def __init__(self, master, app):
        pass
    
    # === View Modes ===
    
    def show_installed_models(self):
        """Show locally installed models."""
        pass
    
    def show_download_browser(self):
        """Show model download/browse interface."""
        pass
    
    # === Installed Models Tab ===
    
    def build_category_list(self):
        """Build category sidebar."""
        pass
    
    def build_model_list(self, category: str):
        """Build scrollable model list for category."""
        pass
    
    def build_details_panel(self):
        """Build model details sidebar."""
        pass
    
    def on_model_selected(self, model: LocalModel):
        """Handle model selection, update details panel."""
        pass
    
    def on_category_selected(self, category: str):
        """Handle category change, refresh model list."""
        pass
    
    # === Batch Operations ===
    
    def get_selected_models(self) -> List[LocalModel]:
        """Get all checked models."""
        pass
    
    def on_delete_selected(self):
        """Delete selected models with confirmation."""
        pass
    
    def on_move_selected(self):
        """Show move dialog, move selected models."""
        pass
    
    def on_copy_selected(self):
        """Show copy dialog, copy selected models."""
        pass
    
    # === Download Browser Tab ===
    
    def build_curated_section(self):
        """Show curated/recommended models."""
        pass
    
    def build_search_section(self):
        """Search bar and results."""
        pass
    
    def on_search(self, query: str):
        """Execute search across repositories."""
        pass
    
    def on_download_model(self, model: RepoModel, file: RepoModelFile):
        """Start model download."""
        pass
    
    # === Verification ===
    
    def on_verify_model(self, model: LocalModel):
        """Verify single model hash."""
        pass
    
    def on_verify_all(self):
        """Verify all models (background task)."""
        pass
```

---

## 12. Workflow Management System

### 12.1 Overview

Workflow management focused on **importing and recommending existing workflows** rather than creating new ones from scratch. This avoids the complexity of ComfyUI's node API.

**Core Capabilities:**
- Browse and import community workflows from curated sources
- Recommend workflows based on use case and installed models
- Organize workflows into user collections
- Validate workflows against installed models/nodes
- One-click workflow loading into ComfyUI

### 12.2 Workflow Sources

**Curated Sources:**
1. **Bundled Workflows** - Ship with the app, tested and validated
2. **ComfyUI Examples** - Official example workflows from ComfyUI repo
3. **OpenArt Workflows** - Community workflows from openart.ai
4. **Civitai Workflows** - Workflows attached to models on CivitAI

### 12.3 Data Schemas

```python
@dataclass
class Workflow:
    """Represents a ComfyUI workflow."""
    
    workflow_id: str                    # Unique identifier
    filename: str                       # "wan_i2v_basic.json"
    filepath: Optional[Path]            # Local path if installed
    
    # Metadata
    display_name: str
    description: str
    author: str
    source: str                         # "bundled", "openart", "civitai", "user"
    source_url: Optional[str]
    
    # Requirements
    required_models: List[str]          # Model IDs that must be installed
    required_nodes: List[str]           # Custom node IDs required
    capabilities: List[str]             # What this workflow does
    
    # Compatibility
    min_comfy_version: Optional[str]
    model_type: str                     # "sdxl", "sd15", "flux", "gguf"
    
    # Preview
    preview_image_url: Optional[str]
    example_outputs: List[str]          # URLs to example outputs
    
    # Status
    installed: bool
    validated: bool                     # All requirements met
    missing_requirements: List[str]     # What's missing if not validated
    
    # Categorization
    tags: List[str]
    category: str                       # "image", "video", "upscale", etc.


@dataclass
class WorkflowCollection:
    """User-created workflow collection/folder."""
    
    collection_id: str
    name: str
    description: str
    workflows: List[str]                # Workflow IDs
    created_at: datetime
```

### 12.4 WorkflowService

**File:** `src/services/workflow_service.py`

```python
class WorkflowService:
    """
    Manages workflow discovery, import, and organization.
    """
    
    COMFY_WORKFLOWS_PATH = "user/default/workflows"
    
    def __init__(self, comfy_path: str):
        self.comfy_path = Path(comfy_path)
        self.workflows_path = self.comfy_path / self.COMFY_WORKFLOWS_PATH
    
    # === Browsing ===
    
    def get_installed_workflows(self) -> List[Workflow]:
        """List all workflows installed in ComfyUI."""
        pass
    
    def get_bundled_workflows(self) -> List[Workflow]:
        """List workflows bundled with the app."""
        pass
    
    def get_curated_workflows(
        self,
        category: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        model_type: Optional[str] = None
    ) -> List[Workflow]:
        """
        Get curated workflows from resources.json.
        
        Args:
            category: Filter by category (image, video, etc.)
            capabilities: Filter by capabilities (t2i, i2v, etc.)
            model_type: Filter by compatible model type
        """
        pass
    
    def search_openart_workflows(
        self,
        query: str,
        limit: int = 20
    ) -> List[Workflow]:
        """Search OpenArt for community workflows."""
        pass
    
    # === Recommendations ===
    
    def get_recommended_workflows(
        self,
        use_case: str,
        installed_models: List[str],
        installed_nodes: List[str]
    ) -> List[Workflow]:
        """
        Get workflows recommended for use case that work with installed components.
        
        Prioritizes:
        1. Workflows where all requirements are already met
        2. Workflows that match the use case capabilities
        3. Higher-rated/more popular workflows
        """
        pass
    
    def get_workflows_for_model(self, model_id: str) -> List[Workflow]:
        """Get workflows that use a specific model."""
        pass
    
    # === Validation ===
    
    def validate_workflow(
        self,
        workflow: Workflow,
        installed_models: List[str],
        installed_nodes: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Check if a workflow can run with current installation.
        
        Returns:
            (is_valid, list_of_missing_requirements)
        """
        pass
    
    def parse_workflow_requirements(self, workflow_json: dict) -> dict:
        """
        Parse a workflow JSON to extract requirements.
        
        Returns:
            {
                "nodes": ["ComfyUI-GGUF", ...],
                "models": ["wan_i2v_high.gguf", ...],
                "model_type": "gguf"
            }
        """
        pass
    
    # === Import/Install ===
    
    def import_workflow(
        self,
        source_path_or_url: str,
        display_name: Optional[str] = None
    ) -> Workflow:
        """
        Import a workflow from file or URL.
        
        - Downloads if URL
        - Copies to workflows directory
        - Parses and validates
        - Creates metadata entry
        """
        pass
    
    def import_bundled_workflow(self, workflow_id: str) -> Workflow:
        """Copy a bundled workflow to user's ComfyUI."""
        pass
    
    def download_workflow(
        self,
        url: str,
        display_name: str
    ) -> Workflow:
        """Download workflow from URL."""
        pass
    
    # === Organization ===
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete an installed workflow."""
        pass
    
    def rename_workflow(self, workflow_id: str, new_name: str) -> Workflow:
        """Rename a workflow."""
        pass
    
    def create_collection(self, name: str, description: str = "") -> WorkflowCollection:
        """Create a new workflow collection."""
        pass
    
    def add_to_collection(self, workflow_id: str, collection_id: str) -> None:
        """Add workflow to a collection."""
        pass
    
    # === Launch ===
    
    def get_workflow_launch_url(self, workflow: Workflow) -> str:
        """
        Get URL to open ComfyUI with this workflow loaded.
        
        Returns URL like: http://localhost:8188/?workflow=path/to/workflow.json
        """
        pass


class OpenArtAdapter:
    """Adapter for OpenArt workflow API."""
    
    BASE_URL = "https://openart.ai"
    API_URL = "https://openart.ai/api"
    
    def search_workflows(self, query: str, **filters) -> List[dict]:
        """Search OpenArt workflows."""
        pass
    
    def get_workflow_details(self, workflow_id: str) -> dict:
        """Get workflow metadata."""
        pass
    
    def get_workflow_json(self, workflow_id: str) -> dict:
        """Download the actual workflow JSON."""
        pass
```

### 12.5 Curated Workflows Schema (Addition to resources.json)

```json
{
  "workflow_repository": {
    "bundled_workflows": [
      {
        "id": "wan_i2v_basic",
        "filename": "wan_i2v_basic.json",
        "display_name": "Image to Video (Basic)",
        "description": "Animate a still image into a short video clip using Wan 2.2",
        "author": "AI Universal Suite",
        "category": "video",
        "capabilities": ["i2v"],
        "model_type": "gguf",
        "required_models": ["wan_i2v_high_q5", "wan_i2v_low_q5"],
        "required_nodes": ["ComfyUI-GGUF", "ComfyUI-VideoHelperSuite"],
        "tags": ["video", "animation", "beginner-friendly"],
        "preview_image": "previews/wan_i2v_basic.png"
      },
      {
        "id": "sdxl_basic_t2i",
        "filename": "sdxl_basic_t2i.json",
        "display_name": "Text to Image (SDXL)",
        "description": "Generate images from text prompts using SDXL",
        "author": "AI Universal Suite",
        "category": "image",
        "capabilities": ["t2i"],
        "model_type": "sdxl",
        "required_models": [],
        "required_nodes": [],
        "tags": ["image", "text-to-image", "beginner-friendly"],
        "preview_image": "previews/sdxl_basic_t2i.png"
      },
      {
        "id": "flux_schnell_t2i",
        "filename": "flux_schnell_t2i.json",
        "display_name": "Text to Image (Flux Schnell)",
        "description": "Fast, high-quality image generation with Flux",
        "author": "AI Universal Suite",
        "category": "image",
        "capabilities": ["t2i"],
        "model_type": "flux",
        "required_models": ["flux_schnell"],
        "required_nodes": [],
        "tags": ["image", "text-to-image", "fast"],
        "preview_image": "previews/flux_schnell_t2i.png"
      }
    ],
    
    "curated_external": [
      {
        "id": "openart_wan_lipsync",
        "source": "openart",
        "source_id": "abc123",
        "display_name": "Wan 2.2 with Lip Sync",
        "description": "Full pipeline for animated talking heads",
        "category": "video",
        "capabilities": ["i2v", "lipsync"],
        "model_type": "gguf",
        "required_nodes": ["ComfyUI-GGUF", "ComfyUI-LatentSyncWrapper"],
        "tags": ["video", "lipsync", "advanced"],
        "url": "https://openart.ai/workflows/..."
      }
    ],
    
    "workflow_sources": {
      "openart": {
        "display_name": "OpenArt",
        "base_url": "https://openart.ai",
        "api_available": true,
        "quality": "community"
      },
      "comfyui_examples": {
        "display_name": "ComfyUI Official",
        "base_url": "https://github.com/comfyanonymous/ComfyUI_examples",
        "api_available": false,
        "quality": "official"
      }
    }
  }
}
```

### 12.6 Workflow Browser UI

**File:** `src/ui/views/workflow_browser.py`

```python
class WorkflowBrowserFrame(ctk.CTkFrame):
    """
    Workflow browsing and management interface.
    
    Layout:
    ┌─────────────────────────────────────────────────────────────┐
    │ [Installed] [Recommended] [Browse]              [Search]    │
    ├─────────────────────────────────────────────────────────────┤
    │ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
    │ │  [Preview]      │ │  [Preview]      │ │  [Preview]      │ │
    │ │                 │ │                 │ │                 │ │
    │ │ Wan I2V Basic   │ │ SDXL Text2Img   │ │ Flux Fast       │ │
    │ │ ✓ Ready         │ │ ⚠ Missing model │ │ ✓ Ready         │ │
    │ │ [Load] [Info]   │ │ [Install Reqs]  │ │ [Load] [Info]   │ │
    │ └─────────────────┘ └─────────────────┘ └─────────────────┘ │
    ├─────────────────────────────────────────────────────────────┤
    │ Showing 12 workflows | Filter: [All ▼] [Video ▼] [Ready ▼] │
    └─────────────────────────────────────────────────────────────┘
    """
    
    def __init__(self, master, app):
        pass
    
    # === View Modes ===
    
    def show_installed(self):
        """Show locally installed workflows."""
        pass
    
    def show_recommended(self):
        """Show workflows recommended for user's setup."""
        pass
    
    def show_browse(self):
        """Show browsable curated workflows."""
        pass
    
    # === Workflow Cards ===
    
    def build_workflow_card(self, workflow: Workflow) -> ctk.CTkFrame:
        """
        Build a workflow card widget.
        
        Shows:
        - Preview image (if available)
        - Name and description
        - Status (ready, missing requirements)
        - Action buttons
        """
        pass
    
    def on_workflow_load(self, workflow: Workflow):
        """Load workflow into ComfyUI."""
        pass
    
    def on_workflow_info(self, workflow: Workflow):
        """Show detailed workflow info dialog."""
        pass
    
    def on_install_requirements(self, workflow: Workflow):
        """Install missing models/nodes for workflow."""
        pass
    
    # === Search & Filter ===
    
    def on_search(self, query: str):
        """Search workflows."""
        pass
    
    def apply_filters(self, category: str, capability: str, status: str):
        """Apply display filters."""
        pass
    
    # === Import ===
    
    def on_import_file(self):
        """Import workflow from local file."""
        pass
    
    def on_import_url(self):
        """Import workflow from URL."""
        pass
```

---

## 13. Recommendation Resolution Algorithm

### 13.1 Overview

The recommendation engine uses a **weighted scoring system** that combines:
1. **User Profile Scores** - Self-reported experience and preferences from onboarding survey
2. **Use Case Parameters** - Specific requirements for content type, style, and quality
3. **Hardware Constraint Scores** - System capabilities normalized to compatibility scores

These combine into a **composite fitness score** for each candidate configuration, allowing dynamic manifest resolution that balances user needs against system reality.

### 13.2 User Profile Schema

Collected during onboarding survey using **1-5 scales with semantic anchors**.

#### Scale Definitions

**Experience Scale:**
| Value | Label | Description |
|-------|-------|-------------|
| 1 | Beginner | Never used this type of tool |
| 2 | Novice | Tried it a few times |
| 3 | Intermediate | Use regularly, understand basics |
| 4 | Advanced | Power user, understand internals |
| 5 | Expert | Could teach others, customize deeply |

**Importance Scale:**
| Value | Label | Description |
|-------|-------|-------------|
| 1 | Not Important | Don't care about this |
| 2 | Nice to Have | Would be good but not essential |
| 3 | Moderately Important | Matters for my workflow |
| 4 | Very Important | Key requirement |
| 5 | Critical | Must have, dealbreaker without it |

**Frequency Scale:**
| Value | Label | Description |
|-------|-------|-------------|
| 1 | Rarely | Once a month or less |
| 2 | Occasionally | Few times a month |
| 3 | Regularly | Weekly |
| 4 | Frequently | Multiple times per week |
| 5 | Daily | Core part of daily workflow |

#### Data Schema

```python
@dataclass
class UserProfile:
    """User's self-reported experience and preferences."""
    
    # === Experience Scores (1-5 Experience Scale) ===
    ai_experience: int              # Experience with AI tools generally
    technical_experience: int       # Comfort with terminals, config files, troubleshooting
    
    # === Derived Proficiency ===
    # Beginner: both <= 2
    # Intermediate: either >= 3
    # Advanced: either >= 4
    # Expert: both >= 4
    proficiency: Literal["Beginner", "Intermediate", "Advanced", "Expert"]
    
    # === Use Case Intent (multi-select) ===
    primary_use_cases: List[str]    # ["image_generation", "video_generation", "image_editing", "productivity"]
    
    # === Content Parameters (per use case) ===
    content_preferences: Dict[str, ContentPreferences]
    
    # === Workflow Preferences (1-5 Importance Scale) ===
    prefer_simple_setup: int        # Prefer fewer models/nodes vs more capability
    prefer_local_processing: int    # Importance of running locally vs API calls
    prefer_open_source: int         # Preference for open models vs proprietary


@dataclass
class ContentPreferences:
    """Detailed parameters about desired output characteristics."""
    
    # === Output Quality Priorities (1-5 Importance Scale) ===
    photorealism: int               # Photorealistic/lifelike output
    artistic_stylization: int       # Stylized/artistic output
    generation_speed: int           # Fast iteration over maximum quality
    output_quality: int             # Maximum fidelity/detail
    consistency: int                # Same character/style across outputs
    editability: int                # Ability to make targeted changes
    
    # === Domain-Specific (shown based on use case) ===
    
    # For video_generation:
    motion_intensity: Optional[int]     # 1=Subtle/documentary, 5=Dynamic/action
    temporal_coherence: Optional[int]   # Importance of smooth, consistent motion
    
    # For image_editing:
    holistic_edits: Optional[int]       # Full-image transforms (style, lighting)
    localized_edits: Optional[int]      # Inpainting, object removal, targeted changes
    
    # For character work:
    character_consistency: Optional[int] # Same face/character across images
    pose_control: Optional[int]          # Specific pose/composition control
    
    # === Style Tags (selected from predefined list) ===
    style_tags: List[str]           # ["portrait", "landscape", "documentary", "action", "anime", etc.]
    
    # === Output Parameters ===
    typical_resolution: str         # "1024x1024", "2048x2048", "video_720p", "video_1080p"
    batch_frequency: int            # How often do you generate? (1-5 Frequency Scale)
    
    # === Advanced Preferences (shown if proficiency >= Advanced) ===
    preferred_approach: Optional[str]   # "minimal_nodes", "enhanced_lightweight", "monolithic", None = auto
    quantization_acceptable: bool       # Accept GGUF/quantized for compatibility?
    
    
@dataclass
class ApproachPreference:
    """
    How the user prefers to solve capability requirements.
    
    Examples:
    - "minimal_nodes": Simplest setup, fewer moving parts
    - "enhanced_lightweight": SDXL + IPAdapter + ControlNet (flexible, proven)
    - "monolithic": Flux.Kontext, Qwen-Edit (single large model does everything)
    """
    approach: Literal["minimal_nodes", "enhanced_lightweight", "monolithic", "auto"]
```

### 13.3 Hardware Constraint Schema

```python
@dataclass
class HardwareConstraints:
    """
    Comprehensive hardware capabilities as constraint scores.
    Captures factors that genuinely impact sustained AI workload performance.
    """
    
    # =========================================================================
    # RAW VALUES (from SystemService)
    # =========================================================================
    
    # --- GPU ---
    gpu_vendor: str                     # "nvidia", "amd", "apple", "intel", "none"
    gpu_name: str                       # "NVIDIA RTX 4090", "Apple M4 Max", etc.
    vram_gb: float                      # Discrete VRAM (0 for integrated)
    gpu_memory_bandwidth_gbps: Optional[float]  # Memory bandwidth (critical for inference)
    cuda_compute_capability: Optional[str]      # "8.9" for RTX 40xx, affects optimizations
    tensor_cores: bool                  # Has tensor cores / neural engine
    multi_gpu: bool                     # Multiple GPUs detected
    gpu_count: int                      # Number of GPUs
    
    # --- CPU ---
    cpu_name: str                       # "Intel Core i9-13900K", "Apple M4 Max"
    cpu_vendor: str                     # "intel", "amd", "apple"
    cpu_cores_physical: int             # Physical cores
    cpu_cores_logical: int              # Logical cores (with hyperthreading)
    cpu_frequency_ghz: float            # Base frequency
    cpu_architecture: str               # "x86_64", "arm64"
    
    # --- Memory ---
    ram_gb: float                       # Total system RAM
    ram_type: str                       # "DDR4", "DDR5", "LPDDR5", "Unified"
    ram_speed_mhz: Optional[int]        # RAM frequency if detectable
    memory_bandwidth_gbps: Optional[float]  # System memory bandwidth
    unified_memory: bool                # Apple Silicon unified memory architecture
    
    # --- Storage ---
    disk_free_gb: float                 # Available space on target drive
    disk_total_gb: float                # Total drive capacity
    storage_type: str                   # "nvme", "sata_ssd", "hdd", "unknown"
    storage_read_speed_mbps: Optional[float]  # Sequential read (if benchmarked)
    
    # --- System ---
    os: str                             # "windows", "macos", "linux"
    os_version: str                     # "11", "14.5", "Ubuntu 24.04"
    form_factor: str                    # "desktop", "laptop", "mini", "workstation"
    power_profile: str                  # "performance", "balanced", "power_saver"
    
    # --- Thermal/Power (estimated or detected) ---
    tdp_watts: Optional[int]            # Thermal design power
    cooling_capacity: str               # "high", "medium", "low" (estimated from form factor)
    on_battery: bool                    # Currently on battery power
    
    # =========================================================================
    # NORMALIZED SCORES (0.0 - 1.0)
    # =========================================================================
    
    vram_score: float                   # 0 = no VRAM, 1 = 24GB+
    ram_score: float                    # 0 = 8GB, 1 = 64GB+
    storage_score: float                # 0 = <50GB free, 1 = 500GB+ free
    compute_score: float                # Combined GPU compute capability
    cpu_score: float                    # CPU capability for preprocessing
    memory_bandwidth_score: float       # Memory bandwidth (critical for Apple Silicon)
    storage_speed_score: float          # Storage speed impact on model loading
    thermal_headroom_score: float       # Sustained performance potential
    
    # =========================================================================
    # HARD LIMITS (binary)
    # =========================================================================
    
    can_run_flux: bool                  # VRAM >= 12GB OR (Apple Silicon AND RAM >= 32GB)
    can_run_sdxl: bool                  # VRAM >= 8GB OR (Apple Silicon AND RAM >= 16GB)
    can_run_video: bool                 # VRAM >= 8GB OR (Apple Silicon AND RAM >= 32GB)
    requires_quantization: bool         # Apple Silicon OR VRAM < 8GB
    can_sustain_load: bool              # Adequate cooling for extended generation
    storage_adequate: bool              # SSD with sufficient space
    
    # =========================================================================
    # DERIVED RECOMMENDATIONS
    # =========================================================================
    
    recommended_batch_size: int         # Based on VRAM/RAM
    recommended_resolution_cap: str     # Based on memory bandwidth
    expected_thermal_throttle: bool     # Will likely throttle under sustained load
    
    
    @classmethod
    def from_environment(cls, env: EnvironmentReport) -> "HardwareConstraints":
        """Compute all constraint scores from raw environment data."""
        
        # === GPU Scoring ===
        if env.gpu_vendor == "apple":
            # Apple Silicon uses unified memory
            effective_vram = env.ram_gb * 0.75
            vram_score = min(1.0, effective_vram / 24)
            
            # Memory bandwidth is critical for Apple Silicon
            # M1: ~68 GB/s, M1 Max: ~400 GB/s, M4 Max: ~546 GB/s
            bandwidth_score = min(1.0, (env.memory_bandwidth_gbps or 200) / 500)
        else:
            vram_score = min(1.0, env.vram_gb / 24)
            # GPU memory bandwidth: RTX 3090 ~936 GB/s, RTX 4090 ~1008 GB/s
            bandwidth_score = min(1.0, (env.gpu_memory_bandwidth_gbps or 500) / 1000)
        
        # === RAM Scoring ===
        ram_score = min(1.0, (env.ram_gb - 8) / 56)  # 8GB = 0, 64GB = 1
        
        # RAM type/speed bonus
        ram_speed_bonus = 0.0
        if env.ram_type == "DDR5" or env.ram_type == "LPDDR5":
            ram_speed_bonus = 0.1
        if env.ram_speed_mhz and env.ram_speed_mhz >= 6000:
            ram_speed_bonus += 0.05
        
        # === Storage Scoring ===
        storage_score = min(1.0, env.disk_free_gb / 500)
        
        # Storage speed scoring
        if env.storage_type == "nvme":
            storage_speed_score = 1.0
        elif env.storage_type == "sata_ssd":
            storage_speed_score = 0.6
        elif env.storage_type == "hdd":
            storage_speed_score = 0.2
        else:
            storage_speed_score = 0.5  # Unknown, assume moderate
        
        # === CPU Scoring ===
        # Cores matter for preprocessing, batching, running multiple processes
        core_score = min(1.0, (env.cpu_cores_physical - 4) / 12)  # 4 = 0, 16 = 1
        
        # Architecture bonus
        arch_bonus = 0.0
        if env.cpu_architecture == "arm64":
            arch_bonus = 0.1  # Efficient for some workloads
        
        cpu_score = min(1.0, core_score + arch_bonus)
        
        # === Compute Score (GPU capability) ===
        if env.gpu_vendor == "nvidia":
            base_compute = vram_score * 1.0
            # Tensor core bonus
            if env.tensor_cores:
                base_compute += 0.1
            # Modern architecture bonus (Ampere+)
            if env.cuda_compute_capability and float(env.cuda_compute_capability) >= 8.0:
                base_compute += 0.1
            compute_score = min(1.0, base_compute)
            
        elif env.gpu_vendor == "apple":
            # Apple Silicon: unified memory + Neural Engine
            compute_score = min(1.0, vram_score * 0.7 + bandwidth_score * 0.3)
            
        elif env.gpu_vendor == "amd":
            compute_score = vram_score * 0.5  # ROCm limited support
            
        else:
            compute_score = cpu_score * 0.2  # CPU only fallback
        
        # === Thermal Headroom Scoring ===
        # Form factor heavily impacts sustained performance
        if env.form_factor == "workstation":
            thermal_base = 1.0
        elif env.form_factor == "desktop":
            thermal_base = 0.9
        elif env.form_factor == "mini":
            thermal_base = 0.6
        elif env.form_factor == "laptop":
            thermal_base = 0.4
        else:
            thermal_base = 0.5
        
        # Power profile adjustment
        if env.power_profile == "power_saver" or env.on_battery:
            thermal_base *= 0.6
        elif env.power_profile == "balanced":
            thermal_base *= 0.85
        
        # Cooling capacity adjustment
        if env.cooling_capacity == "high":
            thermal_headroom_score = thermal_base
        elif env.cooling_capacity == "medium":
            thermal_headroom_score = thermal_base * 0.85
        else:  # low
            thermal_headroom_score = thermal_base * 0.6
        
        # === Hard Limits ===
        effective_vram = env.ram_gb * 0.75 if env.gpu_vendor == "apple" else env.vram_gb
        
        can_run_flux = (effective_vram >= 12) or (env.gpu_vendor == "apple" and env.ram_gb >= 32)
        can_run_sdxl = (effective_vram >= 8) or (env.gpu_vendor == "apple" and env.ram_gb >= 16)
        can_run_video = (effective_vram >= 8) or (env.gpu_vendor == "apple" and env.ram_gb >= 32)
        requires_quantization = env.gpu_vendor == "apple" or env.vram_gb < 8
        
        # Can sustain load: need decent thermals AND not on battery
        can_sustain_load = thermal_headroom_score >= 0.4 and not env.on_battery
        
        # Storage adequate: SSD with enough space
        storage_adequate = env.storage_type != "hdd" and env.disk_free_gb >= 50
        
        # === Derived Recommendations ===
        # Batch size based on available memory
        if effective_vram >= 24:
            recommended_batch_size = 4
        elif effective_vram >= 16:
            recommended_batch_size = 2
        elif effective_vram >= 10:
            recommended_batch_size = 1
        else:
            recommended_batch_size = 1
        
        # Resolution cap based on memory bandwidth
        if bandwidth_score >= 0.8:
            recommended_resolution_cap = "2048x2048"
        elif bandwidth_score >= 0.5:
            recommended_resolution_cap = "1536x1536"
        elif bandwidth_score >= 0.3:
            recommended_resolution_cap = "1024x1024"
        else:
            recommended_resolution_cap = "768x768"
        
        # Expected throttling
        expected_thermal_throttle = thermal_headroom_score < 0.5
        
        return cls(
            # Raw values
            gpu_vendor=env.gpu_vendor,
            gpu_name=env.gpu_name,
            vram_gb=env.vram_gb,
            gpu_memory_bandwidth_gbps=env.gpu_memory_bandwidth_gbps,
            cuda_compute_capability=env.cuda_compute_capability,
            tensor_cores=env.tensor_cores,
            multi_gpu=env.multi_gpu,
            gpu_count=env.gpu_count,
            cpu_name=env.cpu_name,
            cpu_vendor=env.cpu_vendor,
            cpu_cores_physical=env.cpu_cores_physical,
            cpu_cores_logical=env.cpu_cores_logical,
            cpu_frequency_ghz=env.cpu_frequency_ghz,
            cpu_architecture=env.cpu_architecture,
            ram_gb=env.ram_gb,
            ram_type=env.ram_type,
            ram_speed_mhz=env.ram_speed_mhz,
            memory_bandwidth_gbps=env.memory_bandwidth_gbps,
            unified_memory=env.unified_memory,
            disk_free_gb=env.disk_free_gb,
            disk_total_gb=env.disk_total_gb,
            storage_type=env.storage_type,
            storage_read_speed_mbps=env.storage_read_speed_mbps,
            os=env.os,
            os_version=env.os_version,
            form_factor=env.form_factor,
            power_profile=env.power_profile,
            tdp_watts=env.tdp_watts,
            cooling_capacity=env.cooling_capacity,
            on_battery=env.on_battery,
            # Normalized scores
            vram_score=vram_score,
            ram_score=min(1.0, ram_score + ram_speed_bonus),
            storage_score=storage_score,
            compute_score=compute_score,
            cpu_score=cpu_score,
            memory_bandwidth_score=bandwidth_score,
            storage_speed_score=storage_speed_score,
            thermal_headroom_score=thermal_headroom_score,
            # Hard limits
            can_run_flux=can_run_flux,
            can_run_sdxl=can_run_sdxl,
            can_run_video=can_run_video,
            requires_quantization=requires_quantization,
            can_sustain_load=can_sustain_load,
            storage_adequate=storage_adequate,
            # Derived
            recommended_batch_size=recommended_batch_size,
            recommended_resolution_cap=recommended_resolution_cap,
            expected_thermal_throttle=expected_thermal_throttle
        )
    
    def get_summary(self) -> dict:
        """Human-readable summary for UI display."""
        return {
            "gpu": f"{self.gpu_name} ({self.vram_gb}GB)" if self.vram_gb else self.gpu_name,
            "cpu": f"{self.cpu_name} ({self.cpu_cores_physical} cores)",
            "ram": f"{self.ram_gb}GB {self.ram_type}",
            "storage": f"{self.disk_free_gb:.0f}GB free ({self.storage_type})",
            "form_factor": self.form_factor.title(),
            "thermal_status": "Good" if self.thermal_headroom_score >= 0.6 else 
                             "Moderate" if self.thermal_headroom_score >= 0.4 else "Limited",
            "power_status": "On Battery" if self.on_battery else "Plugged In"
        }
    
    def get_warnings(self) -> List[str]:
        """Generate hardware-related warnings."""
        warnings = []
        
        if self.on_battery:
            warnings.append("Running on battery - performance will be limited")
        
        if self.expected_thermal_throttle:
            warnings.append(f"{self.form_factor.title()} may throttle under sustained AI workloads")
        
        if self.storage_type == "hdd":
            warnings.append("HDD detected - model loading will be very slow, SSD recommended")
        
        if not self.storage_adequate:
            warnings.append("Limited storage - may not have space for multiple models")
        
        if self.ram_gb < 16:
            warnings.append("Limited RAM - may struggle with larger models")
        
        if self.gpu_vendor == "amd":
            warnings.append("AMD GPU - some features may have limited support")
        
        if self.form_factor == "laptop" and self.vram_gb >= 8:
            warnings.append("Laptop GPU - expect reduced performance vs desktop equivalent")
        
        return warnings
```

### 13.3.1 SystemService Detection Methods

The `SystemService` needs these detection methods to populate `EnvironmentReport`:

```python
class SystemService:
    """Extended hardware detection for comprehensive environment scanning."""
    
    def detect_form_factor(self) -> str:
        """
        Detect system form factor.
        
        Heuristics:
        - macOS: Check hw.model for MacBook, Mac mini, Mac Pro, iMac
        - Windows: Check Win32_SystemEnclosure ChassisTypes
        - Linux: Check DMI chassis type or battery presence
        """
        if platform.system() == "Darwin":
            model = subprocess.check_output(["sysctl", "-n", "hw.model"]).decode().strip()
            if "MacBook" in model:
                return "laptop"
            elif "Macmini" in model or "Mac mini" in model:
                return "mini"
            elif "MacPro" in model or "Mac Pro" in model:
                return "workstation"
            else:
                return "desktop"
        
        elif platform.system() == "Windows":
            # WMI query for chassis type
            # 3,4,5,6,7 = Desktop, 8,9,10,14 = Laptop, 35 = Mini PC
            try:
                import wmi
                c = wmi.WMI()
                for chassis in c.Win32_SystemEnclosure():
                    types = chassis.ChassisTypes
                    if any(t in [8, 9, 10, 14] for t in types):
                        return "laptop"
                    elif any(t in [35, 36] for t in types):
                        return "mini"
                    elif any(t in [17, 18, 19, 20] for t in types):
                        return "workstation"
                return "desktop"
            except:
                return "desktop"
        
        else:  # Linux
            # Check for battery
            if Path("/sys/class/power_supply/BAT0").exists():
                return "laptop"
            
            # Check DMI chassis type
            chassis_path = Path("/sys/class/dmi/id/chassis_type")
            if chassis_path.exists():
                chassis_type = int(chassis_path.read_text().strip())
                if chassis_type in [8, 9, 10, 14]:
                    return "laptop"
                elif chassis_type in [35, 36]:
                    return "mini"
                elif chassis_type in [17, 18, 19, 20]:
                    return "workstation"
            
            return "desktop"
    
    def detect_storage_type(self, path: str = None) -> str:
        """
        Detect storage type (NVMe, SATA SSD, HDD).
        
        Returns: "nvme", "sata_ssd", "hdd", "unknown"
        """
        if platform.system() == "Darwin":
            # macOS: All modern Macs use NVMe
            return "nvme"
        
        elif platform.system() == "Windows":
            try:
                import wmi
                c = wmi.WMI()
                for disk in c.Win32_DiskDrive():
                    if "NVMe" in disk.Model or "NVME" in disk.Model:
                        return "nvme"
                    elif disk.MediaType == "Fixed hard disk media":
                        # Check for SSD via interface or model name
                        if "SSD" in disk.Model:
                            return "sata_ssd"
                return "hdd"
            except:
                return "unknown"
        
        else:  # Linux
            # Check rotational flag
            try:
                # Get device for target path
                device = subprocess.check_output(
                    ["df", path or "/home"], text=True
                ).split("\n")[1].split()[0]
                
                # Extract base device name
                base_device = device.replace("/dev/", "").rstrip("0123456789p")
                
                # Check if NVMe
                if "nvme" in base_device:
                    return "nvme"
                
                # Check rotational flag
                rotational_path = f"/sys/block/{base_device}/queue/rotational"
                if Path(rotational_path).exists():
                    is_rotational = int(Path(rotational_path).read_text().strip())
                    return "hdd" if is_rotational else "sata_ssd"
                
                return "unknown"
            except:
                return "unknown"
    
    def detect_power_state(self) -> Tuple[str, bool]:
        """
        Detect power profile and battery state.
        
        Returns: (power_profile, on_battery)
        """
        on_battery = False
        power_profile = "balanced"
        
        if platform.system() == "Darwin":
            try:
                pmset = subprocess.check_output(["pmset", "-g", "batt"], text=True)
                on_battery = "Battery Power" in pmset
            except:
                pass
        
        elif platform.system() == "Windows":
            try:
                import ctypes
                
                class SYSTEM_POWER_STATUS(ctypes.Structure):
                    _fields_ = [
                        ("ACLineStatus", ctypes.c_byte),
                        ("BatteryFlag", ctypes.c_byte),
                        ("BatteryLifePercent", ctypes.c_byte),
                        ("Reserved1", ctypes.c_byte),
                        ("BatteryLifeTime", ctypes.c_ulong),
                        ("BatteryFullLifeTime", ctypes.c_ulong),
                    ]
                
                status = SYSTEM_POWER_STATUS()
                ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))
                on_battery = status.ACLineStatus == 0
                
                # Check power plan
                power_plan = subprocess.check_output(
                    ["powercfg", "/getactivescheme"], text=True
                )
                if "High performance" in power_plan:
                    power_profile = "performance"
                elif "Power saver" in power_plan:
                    power_profile = "power_saver"
            except:
                pass
        
        else:  # Linux
            # Check battery status
            bat_path = Path("/sys/class/power_supply/BAT0/status")
            if bat_path.exists():
                status = bat_path.read_text().strip()
                on_battery = status == "Discharging"
            
            # Check for performance governor
            try:
                governor = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor").read_text().strip()
                if governor == "performance":
                    power_profile = "performance"
                elif governor == "powersave":
                    power_profile = "power_saver"
            except:
                pass
        
        return power_profile, on_battery
    
    def detect_ram_details(self) -> Tuple[str, Optional[int]]:
        """
        Detect RAM type and speed.
        
        Returns: (ram_type, ram_speed_mhz)
        """
        ram_type = "Unknown"
        ram_speed = None
        
        if platform.system() == "Darwin":
            try:
                sp = subprocess.check_output(
                    ["system_profiler", "SPMemoryDataType"], text=True
                )
                if "DDR5" in sp or "LPDDR5" in sp:
                    ram_type = "LPDDR5"
                elif "DDR4" in sp or "LPDDR4" in sp:
                    ram_type = "LPDDR4"
                
                # Apple Silicon uses unified memory
                cpu_info = subprocess.check_output(
                    ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
                )
                if "Apple" in cpu_info:
                    ram_type = "Unified"
            except:
                pass
        
        elif platform.system() == "Windows":
            try:
                import wmi
                c = wmi.WMI()
                for mem in c.Win32_PhysicalMemory():
                    # Memory type codes: 26 = DDR4, 34 = DDR5
                    if mem.SMBIOSMemoryType == 34:
                        ram_type = "DDR5"
                    elif mem.SMBIOSMemoryType == 26:
                        ram_type = "DDR4"
                    
                    if mem.Speed:
                        ram_speed = int(mem.Speed)
                    break
            except:
                pass
        
        else:  # Linux
            try:
                dmidecode = subprocess.check_output(
                    ["sudo", "dmidecode", "-t", "memory"], text=True
                )
                if "DDR5" in dmidecode:
                    ram_type = "DDR5"
                elif "DDR4" in dmidecode:
                    ram_type = "DDR4"
                
                # Parse speed
                for line in dmidecode.split("\n"):
                    if "Speed:" in line and "MHz" in line:
                        speed_str = line.split(":")[1].strip().split()[0]
                        try:
                            ram_speed = int(speed_str)
                        except:
                            pass
                        break
            except:
                pass
        
        return ram_type, ram_speed
    
    def detect_memory_bandwidth(self) -> Optional[float]:
        """
        Estimate or detect memory bandwidth in GB/s.
        
        For Apple Silicon, this is critical for performance.
        """
        if platform.system() == "Darwin":
            try:
                cpu = subprocess.check_output(
                    ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
                ).strip()
                
                # Known Apple Silicon bandwidths
                bandwidth_map = {
                    "M1": 68.25,
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
                
                for chip, bw in bandwidth_map.items():
                    if chip in cpu:
                        return bw
                
                return 100  # Default for unknown Apple Silicon
            except:
                return None
        
        # For discrete GPUs, would need nvidia-smi or similar
        return None
    
    def estimate_cooling_capacity(self, form_factor: str, gpu_tdp: Optional[int] = None) -> str:
        """
        Estimate cooling capacity based on form factor and components.
        """
        if form_factor == "workstation":
            return "high"
        elif form_factor == "desktop":
            # Desktop with high-end GPU may still have limited cooling
            if gpu_tdp and gpu_tdp > 350:
                return "medium"  # Pushing limits
            return "high"
        elif form_factor == "mini":
            return "low"
        elif form_factor == "laptop":
            if gpu_tdp and gpu_tdp > 100:
                return "low"  # Gaming laptop but still limited
            return "low"
        
        return "medium"
```

### 13.4 Comprehensive Capability Taxonomy

Based on research across the current AI image/video generation landscape, this taxonomy covers all capability dimensions that inform model recommendations.

#### 13.4.1 Primary Use Case Categories

```python
class UseCase(Enum):
    """Top-level use case categories."""
    
    # Image Generation
    TEXT_TO_IMAGE = "t2i"           # Generate images from text prompts
    IMAGE_TO_IMAGE = "i2i"          # Transform existing images
    
    # Video Generation  
    IMAGE_TO_VIDEO = "i2v"          # Animate still images
    TEXT_TO_VIDEO = "t2v"           # Generate video from text
    VIDEO_TO_VIDEO = "v2v"          # Transform/edit existing video
    
    # Editing & Enhancement
    IMAGE_EDITING = "edit"          # Modify specific parts of images
    UPSCALING = "upscale"           # Super-resolution enhancement
    FACE_RESTORATION = "face_restore"  # Face enhancement/repair
    
    # Specialized
    LORA_TRAINING = "lora_train"    # Custom model fine-tuning
    WORKFLOW_AUTOMATION = "automation"  # Batch/pipeline processing
```

#### 13.4.2 Model Capability Dimensions

Each model is scored across these dimensions (0.0-1.0):

```python
@dataclass
class ModelCapabilityScores:
    """
    Comprehensive capability scores for model evaluation.
    All scores are 0.0-1.0 normalized.
    """
    
    # === OUTPUT QUALITY ===
    photorealism: float             # Lifelike, photographic quality
    artistic_stylization: float     # Stylized/artistic output capability
    output_fidelity: float          # Maximum detail and resolution
    prompt_adherence: float         # How well it follows text prompts
    text_rendering: float           # Accuracy of text in images
    anatomy_accuracy: float         # Correct human anatomy (hands, faces, bodies)
    
    # === SPEED & EFFICIENCY ===
    generation_speed: float         # Fast iteration capability
    vram_efficiency: float          # Memory usage optimization
    batch_capability: float         # Multiple outputs per run
    
    # === EDITING CAPABILITIES ===
    inpainting: float               # Fill masked regions
    outpainting: float              # Extend canvas/boundaries
    holistic_editing: float         # Full-image transforms (style, lighting, mood)
    localized_editing: float        # Targeted changes (object swap, removal)
    object_removal: float           # Clean removal of unwanted elements
    background_replacement: float   # Seamless background swapping
    
    # === STRUCTURAL CONTROL ===
    pose_control: float             # OpenPose/skeleton control
    edge_control: float             # Canny edge guidance
    depth_control: float            # Depth map conditioning
    composition_control: float      # Layout/composition guidance
    segmentation_control: float     # Semantic region control
    
    # === IDENTITY & CONSISTENCY ===
    character_consistency: float    # Same character across generations
    face_id_preservation: float     # Specific face identity retention
    style_consistency: float        # Consistent visual style
    subject_consistency: float      # Same object/subject retention
    
    # === VIDEO-SPECIFIC ===
    motion_subtlety: float          # Subtle/documentary motion
    motion_dynamic: float           # Energetic/action motion
    temporal_coherence: float       # Smooth, consistent motion
    motion_diversity: float         # Range of motion types
    video_length: float             # Support for longer clips
    frame_rate: float               # Output FPS capability
    
    # === ENHANCEMENT COMPATIBILITY ===
    ipadapter_compatible: float     # Works with IPAdapter
    controlnet_compatible: float    # Works with ControlNet
    lora_trainable: float           # Can be fine-tuned with LoRA
    upscaler_friendly: float        # Outputs work well with upscalers
    
    # === SPECIALIZED ===
    product_photography: float      # E-commerce/product shots
    portrait_quality: float         # Human portraits
    landscape_quality: float        # Scenic/environment images
    concept_art: float              # Conceptual/design work
    anime_manga: float              # Anime/manga style
    architectural: float            # Buildings/interior design
```

#### 13.4.3 User Preference Dimensions

Users express preferences using the 1-5 semantic scale:

```python
@dataclass  
class UserPreferences:
    """
    User preferences collected via onboarding survey.
    All values 1-5 with semantic labels.
    """
    
    # === EXPERIENCE (Experience Scale: Beginner→Expert) ===
    ai_tools_experience: int        # Familiarity with AI generation tools
    technical_experience: int       # Comfort with setup/configuration
    
    # === OUTPUT PRIORITIES (Importance Scale: Not Important→Critical) ===
    photorealism_priority: int
    artistic_priority: int
    speed_priority: int
    quality_priority: int
    consistency_priority: int
    editability_priority: int
    
    # === EDITING NEEDS (if image_editing use case) ===
    holistic_edits_need: int        # Full-image transforms
    localized_edits_need: int       # Targeted changes
    object_removal_need: int        # Remove unwanted elements
    background_work_need: int       # Background replacement
    
    # === VIDEO NEEDS (if video use case) ===
    motion_style: Literal["subtle", "moderate", "dynamic"]
    temporal_quality_need: int      # Smooth motion importance
    video_length_need: int          # Longer clips importance
    
    # === CONTROL NEEDS ===
    pose_control_need: int          # Specific poses
    composition_control_need: int   # Layout control
    character_consistency_need: int # Same character across outputs
    
    # === DOMAIN (multi-select style tags) ===
    domains: List[str]              # ["portrait", "product", "documentary", ...]
    
    # === WORKFLOW PREFERENCES ===
    prefer_simple_setup: int        # Fewer components
    prefer_fast_iteration: int      # Quick results over quality
    prefer_maximum_quality: int     # Best output over speed
    accept_quantization: bool       # OK with quality tradeoff for compatibility
    
    # === APPROACH PREFERENCE (Advanced users only) ===
    preferred_approach: Optional[Literal[
        "minimal",              # Single checkpoint, simplest
        "enhanced_lightweight", # Checkpoint + IPAdapter + ControlNet
        "monolithic",          # Single powerful model (Flux.Kontext, Qwen-Edit)
        "custom_training",     # LoRA/DreamBooth for specific needs
        "auto"                 # Let system decide
    ]]
```

#### 13.4.4 Model Family Reference

```python
MODEL_FAMILIES = {
    # === Image Generation ===
    "sd15": {
        "display": "Stable Diffusion 1.5",
        "strengths": ["fast", "lora_ecosystem", "controlnet_mature"],
        "weaknesses": ["lower_quality", "512_native"],
        "min_vram": 4, "recommended_vram": 6
    },
    "sdxl": {
        "display": "Stable Diffusion XL",
        "strengths": ["quality", "1024_native", "ecosystem"],
        "weaknesses": ["slower", "vram_hungry"],
        "min_vram": 8, "recommended_vram": 12
    },
    "sd3": {
        "display": "Stable Diffusion 3.x",
        "strengths": ["text_rendering", "mmdit_architecture"],
        "weaknesses": ["licensing", "ecosystem_young"],
        "min_vram": 10, "recommended_vram": 16
    },
    "flux": {
        "display": "Flux (Black Forest Labs)",
        "variants": ["dev", "schnell", "kontext", "fill", "depth", "canny", "redux"],
        "strengths": ["quality", "text_rendering", "prompt_adherence", "editing"],
        "weaknesses": ["slow", "vram_hungry", "large_models"],
        "min_vram": 12, "recommended_vram": 24
    },
    "qwen": {
        "display": "Qwen Vision-Language",
        "variants": ["qwen_vl_edit", "qwen_image"],
        "strengths": ["holistic_editing", "instruction_following", "multimodal"],
        "weaknesses": ["specialized", "newer_ecosystem"],
        "min_vram": 10, "recommended_vram": 16
    },
    
    # === Video Generation ===
    "wan": {
        "display": "Wan 2.x (Alibaba)",
        "strengths": ["quality", "efficiency", "i2v_excellence", "bilingual"],
        "weaknesses": ["compute_heavy", "newer"],
        "variants": ["wan_t2v_14b", "wan_t2v_1.3b", "wan_i2v"],
        "min_vram": 8, "min_ram": 32, "gguf_available": True
    },
    "hunyuan": {
        "display": "HunyuanVideo (Tencent)",
        "strengths": ["quality", "temporal_coherence", "t2v", "i2v"],
        "weaknesses": ["slow", "vram_hungry", "80gb_ideal"],
        "min_vram": 12, "min_ram": 48
    },
    "ltx": {
        "display": "LTX-Video (Lightricks)",
        "strengths": ["speed", "realtime", "consumer_gpu"],
        "weaknesses": ["lower_resolution", "shorter_clips"],
        "min_vram": 8, "recommended_vram": 12
    },
    "mochi": {
        "display": "Mochi 1 (Genmo)",
        "strengths": ["motion_quality", "physics", "apache_license"],
        "weaknesses": ["slow", "10b_parameters"],
        "min_vram": 12, "min_ram": 32
    },
    "cogvideo": {
        "display": "CogVideoX (Tsinghua)",
        "strengths": ["lora_support", "ecosystem", "quantization"],
        "weaknesses": ["720p_max", "6_second_limit"],
        "min_vram": 8
    },
    
    # === Enhancement Models ===
    "upscaler": {
        "display": "Upscaling Models",
        "models": ["real_esrgan", "swinir", "bsrgan", "4x_ultrasharp"],
        "purpose": "super_resolution"
    },
    "face_restore": {
        "display": "Face Restoration",
        "models": ["gfpgan", "codeformer", "restoreformer"],
        "purpose": "face_enhancement"
    }
}
```

#### 13.4.5 Enhancement/Node Ecosystem

```python
ENHANCEMENT_NODES = {
    "ipadapter": {
        "display": "IPAdapter",
        "purpose": "Image prompt conditioning - copy style, composition, or face",
        "variants": ["standard", "plus", "face_id", "face_id_plus", "face_id_plusv2"],
        "best_for": ["style_transfer", "character_consistency", "composition_reference"],
        "compatible_with": ["sd15", "sdxl", "flux"],
        "complexity": "medium"
    },
    "controlnet": {
        "display": "ControlNet",
        "purpose": "Structural conditioning - pose, edges, depth, segmentation",
        "variants": ["openpose", "canny", "depth", "scribble", "seg", "tile", "softedge"],
        "best_for": ["pose_control", "composition_control", "structural_guidance"],
        "compatible_with": ["sd15", "sdxl", "flux"],
        "complexity": "medium"
    },
    "insightface": {
        "display": "InsightFace",
        "purpose": "Face detection and embedding for identity preservation",
        "best_for": ["face_swap", "character_consistency"],
        "compatible_with": ["sd15", "sdxl"],
        "complexity": "medium"
    },
    "lora": {
        "display": "LoRA Fine-tuning",
        "purpose": "Lightweight model customization for specific styles/subjects",
        "training_for": ["style", "character", "concept", "aesthetic"],
        "compatible_with": ["sd15", "sdxl", "flux", "wan"],
        "complexity": "high"
    }
}
```

#### 13.4.6 Workflow Pattern Templates

```python
WORKFLOW_PATTERNS = {
    "quick_iteration": {
        "description": "Fast results for experimentation",
        "recommended_for": ["prototyping", "exploration", "testing_prompts"],
        "models": ["flux_schnell", "sdxl_turbo", "ltx_video"],
        "priority": "speed"
    },
    "maximum_quality": {
        "description": "Best possible output, time secondary",
        "recommended_for": ["final_delivery", "print", "portfolio"],
        "models": ["flux_dev", "juggernaut_xl", "hunyuan_video"],
        "priority": "quality"
    },
    "character_pipeline": {
        "description": "Consistent character across multiple images",
        "recommended_for": ["comics", "storyboards", "character_design"],
        "approach": "enhanced_lightweight",
        "nodes": ["ipadapter_face_id", "controlnet_openpose"],
        "models": ["sdxl + ipadapter", "flux_kontext"]
    },
    "photo_editing": {
        "description": "Edit existing photographs",
        "recommended_for": ["retouching", "background_change", "object_removal"],
        "models": ["flux_fill", "qwen_vl_edit", "sdxl_inpainting"],
        "priority": "editability"
    },
    "documentary_video": {
        "description": "Subtle motion for historical/documentary content",
        "recommended_for": ["photo_animation", "historical", "subtle_movement"],
        "models": ["wan_i2v_gguf", "hunyuan_i2v"],
        "motion_style": "subtle"
    },
    "action_video": {
        "description": "Dynamic motion for energetic content",
        "recommended_for": ["action", "social_media", "dynamic_content"],
        "models": ["hunyuan_video", "mochi"],
        "motion_style": "dynamic"
    },
    "product_photography": {
        "description": "E-commerce and product shots",
        "recommended_for": ["ecommerce", "catalog", "marketing"],
        "models": ["flux_dev", "juggernaut_xl"],
        "nodes": ["controlnet_depth"],
        "priority": "photorealism"
    },
    "artistic_exploration": {
        "description": "Creative and stylized output",
        "recommended_for": ["art", "concept_design", "experimentation"],
        "models": ["dreamshaper_xl", "flux_redux"],
        "priority": "artistic_stylization"
    }
}
```

### 13.5 Model Candidate Scoring Algorithm

The scoring algorithm matches user preferences against model capabilities:

```python
def score_model_candidate(
    candidate: ModelCandidate,
    user_prefs: UserPreferences,
    hardware: HardwareConstraints,
    use_case: str
) -> ModelCandidate:
    """
    Compute fitness scores for a model candidate.
    
    Three score components:
    1. Hardware Fit (50%) - Can it run? How well?
    2. User Fit (35%) - Does it match preferences?
    3. Approach Fit (15%) - Does setup match workflow preference?
    """
    
    # === HARDWARE FIT (hard limits first, then soft penalties) ===
    hw_score = compute_hardware_fit(candidate, hardware)
    if hw_score == 0.0:
        candidate.composite_score = 0.0
        candidate.rejection_reason = candidate.hardware_reasoning[0]
        return candidate
    
    # === USER FIT (weighted preference matching) ===
    # Build weight vector from user importance ratings
    weights = build_preference_weights(user_prefs, use_case)
    
    # Compute weighted dot product of user priorities vs model capabilities
    user_score = 0.0
    for dimension, weight in weights.items():
        model_capability = getattr(candidate.capabilities, dimension, 0.0)
        user_score += weight * model_capability
    
    # Domain/style tag bonus
    user_score += compute_domain_bonus(candidate, user_prefs)
    
    candidate.user_fit_score = min(1.0, user_score)
    
    # === APPROACH FIT ===
    approach_score = compute_approach_fit(
        candidate.approach,
        user_prefs.preferred_approach,
        user_prefs.prefer_simple_setup,
        len(candidate.required_nodes)
    )
    candidate.approach_fit_score = approach_score
    
    # === COMPOSITE SCORE ===
    candidate.composite_score = (
        0.50 * hw_score +
        0.35 * candidate.user_fit_score +
        0.15 * approach_score
    )
    
    return candidate


def build_preference_weights(prefs: UserPreferences, use_case: str) -> Dict[str, float]:
    """
    Convert user 1-5 importance ratings to normalized weights.
    Include use-case-specific dimensions.
    """
    raw_weights = {
        "photorealism": normalize_score(prefs.photorealism_priority),
        "artistic_stylization": normalize_score(prefs.artistic_priority),
        "generation_speed": normalize_score(prefs.speed_priority),
        "output_fidelity": normalize_score(prefs.quality_priority),
        "character_consistency": normalize_score(prefs.consistency_priority),
    }
    
    # Add use-case-specific dimensions
    if use_case == "edit":
        raw_weights["holistic_editing"] = normalize_score(prefs.holistic_edits_need)
        raw_weights["localized_editing"] = normalize_score(prefs.localized_edits_need)
        raw_weights["object_removal"] = normalize_score(prefs.object_removal_need)
        raw_weights["background_replacement"] = normalize_score(prefs.background_work_need)
    
    if use_case in ["i2v", "t2v"]:
        if prefs.motion_style == "subtle":
            raw_weights["motion_subtlety"] = 0.8
            raw_weights["motion_dynamic"] = 0.2
        elif prefs.motion_style == "dynamic":
            raw_weights["motion_subtlety"] = 0.2
            raw_weights["motion_dynamic"] = 0.8
        else:  # moderate
            raw_weights["motion_subtlety"] = 0.5
            raw_weights["motion_dynamic"] = 0.5
        
        raw_weights["temporal_coherence"] = normalize_score(prefs.temporal_quality_need)
    
    if prefs.pose_control_need >= 3:
        raw_weights["pose_control"] = normalize_score(prefs.pose_control_need)
    
    if prefs.composition_control_need >= 3:
        raw_weights["composition_control"] = normalize_score(prefs.composition_control_need)
    
    # Normalize to sum to 1.0
    total = sum(raw_weights.values())
    return {k: v / total for k, v in raw_weights.items()} if total > 0 else raw_weights


def compute_domain_bonus(candidate: ModelCandidate, prefs: UserPreferences) -> float:
    """
    Bonus for matching user's domain/style tags.
    +0.05 per match, max +0.20
    """
    model_domains = set(candidate.model_info.get("domains", []))
    user_domains = set(prefs.domains)
    matches = len(model_domains & user_domains)
    return min(0.20, matches * 0.05)


def compute_hardware_fit(candidate: ModelCandidate, hardware: HardwareConstraints) -> float:
    """
    Compute hardware fitness score with comprehensive system consideration.
    Returns 0.0 if model cannot run, otherwise 0.0-1.0 based on fit quality.
    """
    hw_fit = 1.0
    reasoning = []
    
    # === HARD LIMITS ===
    effective_vram = hardware.ram_gb * 0.75 if hardware.unified_memory else hardware.vram_gb
    if candidate.min_vram_gb > effective_vram:
        if candidate.model_info.get("has_gguf") or candidate.model_info.get("has_fp8"):
            hw_fit -= 0.15
            reasoning.append("Requires quantized version")
        else:
            return 0.0
    
    if candidate.min_ram_gb > hardware.ram_gb:
        return 0.0
    
    if candidate.size_gb > hardware.disk_free_gb * 0.8:
        return 0.0
    elif candidate.size_gb > hardware.disk_free_gb * 0.5:
        hw_fit -= 0.15
        reasoning.append("Storage will be tight")
    
    # === SOFT PENALTIES ===
    if hardware.storage_type == "hdd":
        hw_fit -= 0.20
        reasoning.append("HDD - slow model loading")
    
    if not hardware.can_sustain_load and candidate.capabilities.generation_speed < 0.4:
        hw_fit -= 0.20
        reasoning.append("May throttle during generation")
    
    if hardware.form_factor == "laptop" and candidate.min_vram_gb >= 10:
        hw_fit -= 0.10
    elif hardware.form_factor == "mini" and candidate.min_vram_gb >= 8:
        hw_fit -= 0.15
    
    if hardware.on_battery:
        hw_fit -= 0.25
    
    if hardware.unified_memory and hardware.memory_bandwidth_score < 0.5:
        if candidate.capabilities.output_fidelity > 0.8:
            hw_fit -= 0.10
    
    candidate.hardware_reasoning = reasoning
    return max(0.0, min(1.0, hw_fit))


def compute_approach_fit(
    model_approach: str,
    user_preference: Optional[str],
    simplicity_preference: int,
    node_count: int
) -> float:
    """Score how well model's setup approach matches user preference."""
    if not user_preference or user_preference == "auto":
        return 0.6 if node_count > 3 else 0.8
    
    if model_approach == user_preference:
        return 1.0
    
    compatibility = {
        ("minimal", "enhanced_lightweight"): 0.5,
        ("enhanced_lightweight", "minimal"): 0.6,
        ("monolithic", "minimal"): 0.7,
        ("minimal", "monolithic"): 0.7,
    }
    base = compatibility.get((model_approach, user_preference), 0.3)
    
    if simplicity_preference >= 4 and node_count > 3:
        base -= 0.2
    
    return max(0.0, min(1.0, base))


def normalize_score(value: int) -> float:
    """Convert 1-5 user input to 0-1 normalized score."""
    return (value - 1) / 4
```

### 13.6 Resolution Process

```
┌─────────────────────────────────────────────────────────────────┐
│              WEIGHTED RECOMMENDATION RESOLUTION                  │
└─────────────────────────────────────────────────────────────────┘

INPUT:
├── user_profile: UserProfile       # From onboarding survey
├── env: EnvironmentReport          # From hardware scan
└── advanced_mode: bool             # Expert override enabled?

PHASE 1: Normalize Inputs
├── Compute HardwareConstraints from env
├── Determine proficiency level from experience scores
├── Extract content preferences for each selected use case
└── Output: HardwareConstraints, proficiency, Dict[use_case, ContentPreferences]

PHASE 2: Generate Candidate Pool
├── For each selected use_case:
│   ├── Load all models with matching capabilities
│   ├── Load all workflows with matching capabilities
│   └── Load all custom nodes required by candidates
└── Output: List[ModelCandidate], List[WorkflowCandidate], List[str] nodes

PHASE 3: Score All Candidates
├── For each ModelCandidate:
│   ├── Compute user_fit_score against content preferences
│   ├── Compute hardware_fit_score against constraints
│   ├── Compute composite_score
│   └── Record reasoning for score components
├── For each WorkflowCandidate:
│   ├── Check required models exist in passing candidates
│   ├── Check required nodes are available
│   └── Compute workflow_fit_score
└── Output: Scored candidates with reasoning

PHASE 4: Apply Hard Constraints (Guardrails)
├── REJECT models where:
│   ├── hardware_fit_score == 0.0 (cannot run)
│   ├── min_vram > available AND no GGUF variant
│   └── size_gb > disk_free_gb
├── REJECT workflows where:
│   ├── Any required model was rejected
│   └── Any required node is incompatible with OS
├── WARN but allow if:
│   ├── Model requires quantization (suggest GGUF)
│   └── Storage is tight but sufficient
└── Output: Filtered candidates, warnings

PHASE 5: Rank and Select
├── Sort ModelCandidates by composite_score DESC
├── Select top model per capability needed:
│   ├── Best t2i model
│   ├── Best i2i model (if capability requested)
│   ├── Best i2v model (if capability requested)
│   └── etc.
├── Select workflows compatible with selected models
├── Collect all required custom nodes
└── Output: Selected models, workflows, nodes

PHASE 6: Expert Override (if advanced_mode)
├── Present full candidate list with scores
├── Allow manual selection/deselection
├── Re-validate against hard constraints
└── Output: User-modified selection

PHASE 7: Generate Manifest
├── For each selected model:
│   ├── Resolve download URL (prefer GGUF if requires_quantization)
│   ├── Compute expected hash
│   └── Determine destination directory
├── For each selected workflow:
│   └── Resolve file path
├── For each required node:
│   └── Resolve git repo URL
├── Calculate total size and time estimate
└── Output: InstallationManifest

PHASE 8: Generate Output
├── Compile reasoning from all scoring decisions
├── Compile warnings from constraint checks
├── Calculate overall confidence score
└── Output: RecommendationResult
```

### 13.7 Scoring Weights Configuration

Stored in `resources.json` to allow tuning without code changes:

```json
{
  "recommendation_config": {
    "scoring_weights": {
      "composite": {
        "hardware_fit": 0.50,
        "user_fit": 0.35,
        "approach_fit": 0.15
      },
      "user_fit_components": {
        "style_tag_match_bonus": 0.05,
        "style_tag_max_bonus": 0.20
      },
      "hardware_penalties": {
        "quantization_required": -0.15,
        "storage_over_50pct": -0.15,
        "storage_hdd": -0.20,
        "storage_sata_large_model": -0.05,
        "thermal_throttle_risk": -0.20,
        "laptop_demanding_model": -0.10,
        "mini_demanding_model": -0.15,
        "on_battery": -0.25,
        "low_bandwidth_high_quality": -0.10,
        "slow_model_slow_hw": -0.15
      },
      "hardware_bonuses": {
        "good_thermal_demanding_model": 0.05
      },
      "approach_penalties": {
        "too_many_nodes_for_simplicity": -0.20,
        "approach_mismatch": -0.40
      }
    },
    
    "proficiency_thresholds": {
      "beginner": {"ai_max": 2, "tech_max": 2},
      "intermediate": {"either_min": 3},
      "advanced": {"either_min": 4},
      "expert": {"both_min": 4}
    },
    
    "scale_normalization": {
      "input_min": 1,
      "input_max": 5,
      "output_min": 0.0,
      "output_max": 1.0
    },
    
    "hardware_normalization": {
      "vram_max_gb": 24,
      "ram_min_gb": 8,
      "ram_max_gb": 64,
      "storage_max_gb": 500,
      "bandwidth_max_gbps": 1000,
      "apple_bandwidth_max_gbps": 546,
      "apple_silicon_vram_factor": 0.75,
      "apple_silicon_compute_factor": 0.7,
      "amd_compute_factor": 0.5,
      "cpu_compute_factor": 0.2,
      "cpu_cores_min": 4,
      "cpu_cores_max": 16
    },
    
    "thermal_scoring": {
      "workstation": 1.0,
      "desktop": 0.9,
      "mini": 0.6,
      "laptop": 0.4,
      "power_saver_factor": 0.6,
      "balanced_factor": 0.85,
      "performance_factor": 1.0,
      "cooling_high_factor": 1.0,
      "cooling_medium_factor": 0.85,
      "cooling_low_factor": 0.6
    },
    
    "storage_scoring": {
      "nvme": 1.0,
      "sata_ssd": 0.6,
      "hdd": 0.2,
      "unknown": 0.5
    },
    
    "hard_limits": {
      "flux_min_vram": 12,
      "flux_apple_min_ram": 32,
      "sdxl_min_vram": 8,
      "sdxl_apple_min_ram": 16,
      "video_min_vram": 8,
      "video_apple_min_ram": 32,
      "storage_max_usage_pct": 0.8,
      "storage_warning_pct": 0.5,
      "ram_buffer_gb": 2,
      "min_storage_gb": 50,
      "thermal_sustain_threshold": 0.4
    },
    
    "form_factor_limits": {
      "laptop": {
        "demanding_model_vram_threshold": 10,
        "max_recommended_model_size_gb": 20
      },
      "mini": {
        "demanding_vram_threshold": 8,
        "demanding_size_threshold_gb": 15,
        "max_recommended_model_size_gb": 15
      },
      "desktop": {
        "max_recommended_model_size_gb": 50
      },
      "workstation": {
        "max_recommended_model_size_gb": 100
      }
    },
    
    "bandwidth_thresholds": {
      "high_quality_min_score": 0.5,
      "resolution_caps": {
        "0.8": "2048x2048",
        "0.5": "1536x1536",
        "0.3": "1024x1024",
        "0.0": "768x768"
      }
    },
    
    "domain_scoring": {
      "video_generation": {
        "motion_intensity_mapping": {
          "1-2": "motion_subtlety",
          "4-5": "motion_dynamic",
          "3": "balanced"
        }
      },
      "image_editing": {
        "edit_type_mapping": {
          "holistic_heavy": ["qwen_vl_edit", "flux_kontext"],
          "localized_heavy": ["sdxl_inpainting", "flux_fill"]
        }
      }
    },
    
    "approach_complexity": {
      "minimal": {
        "max_nodes": 2,
        "description": "Fewest moving parts"
      },
      "enhanced_lightweight": {
        "max_nodes": 5,
        "description": "Base model + specialized nodes"
      },
      "monolithic": {
        "max_nodes": 1,
        "description": "Single powerful model"
      }
    }
  }
}
```

### 13.8 Model Metadata Schema (Addition to resources.json)

Each model entry needs scoring attributes across all capability dimensions:

```json
{
  "comfyui_components": {
    "models": {
      "checkpoints": {
        "juggernaut_xl_v9": {
          "display_name": "Juggernaut XL v9",
          "url": "https://...",
          "size_gb": 6.5,
          "hash_sha256": "abc123...",
          
          "capabilities": ["t2i", "i2i"],
          "model_family": "sdxl",
          "has_gguf": false,
          
          "requirements": {
            "min_vram_gb": 8,
            "min_ram_gb": 16
          },
          
          "approach": "minimal",
          "requires_nodes": [],
          
          "scoring": {
            "photorealism": 0.95,
            "artistic_style": 0.3,
            "speed": 0.6,
            "quality": 0.9,
            "consistency": 0.4,
            "editability": 0.3,
            
            "character_consistency": 0.3,
            "pose_control": 0.2
          },
          
          "style_tags": ["photorealistic", "portrait", "landscape", "product", "documentary"],
          
          "notes": "Excellent photorealism, limited character consistency without additional nodes"
        },
        
        "dreamshaper_xl": {
          "display_name": "DreamShaper XL",
          "url": "https://...",
          "size_gb": 6.5,
          "hash_sha256": "def456...",
          
          "capabilities": ["t2i", "i2i"],
          "model_family": "sdxl",
          "has_gguf": false,
          
          "requirements": {
            "min_vram_gb": 8,
            "min_ram_gb": 16
          },
          
          "approach": "minimal",
          "requires_nodes": [],
          
          "scoring": {
            "photorealism": 0.5,
            "artistic_style": 0.9,
            "speed": 0.6,
            "quality": 0.85,
            "consistency": 0.5,
            "editability": 0.3,
            
            "character_consistency": 0.4,
            "pose_control": 0.2
          },
          
          "style_tags": ["artistic", "fantasy", "anime", "stylized", "concept_art"],
          
          "notes": "Strong stylization, good for creative/artistic work"
        }
      },
      
      "enhanced_configurations": {
        "sdxl_ipadapter_controlnet": {
          "display_name": "SDXL + IPAdapter + ControlNet",
          "description": "Lightweight base model enhanced with specialized nodes for character consistency and pose control",
          
          "base_model": "juggernaut_xl_v9",
          "requires_nodes": ["ComfyUI-IPAdapter-Plus", "comfyui_controlnet_aux", "ComfyUI-InsightFace"],
          
          "capabilities": ["t2i", "i2i", "character_ref", "pose_ref"],
          "approach": "enhanced_lightweight",
          
          "total_size_gb": 8.5,
          "requirements": {
            "min_vram_gb": 10,
            "min_ram_gb": 16
          },
          
          "scoring": {
            "photorealism": 0.9,
            "artistic_style": 0.4,
            "speed": 0.4,
            "quality": 0.85,
            "consistency": 0.85,
            "editability": 0.5,
            
            "character_consistency": 0.9,
            "pose_control": 0.85
          },
          
          "style_tags": ["photorealistic", "portrait", "character", "consistent"],
          
          "notes": "Best balance of character consistency with proven, stable workflow"
        }
      },
      
      "monolithic_models": {
        "flux_kontext": {
          "display_name": "Flux Kontext",
          "url": "https://...",
          "size_gb": 23.8,
          "hash_sha256": "...",
          
          "capabilities": ["t2i", "i2i", "edit", "character_ref"],
          "model_family": "flux",
          "has_gguf": true,
          
          "requirements": {
            "min_vram_gb": 12,
            "min_ram_gb": 32
          },
          
          "approach": "monolithic",
          "requires_nodes": [],
          
          "scoring": {
            "photorealism": 0.95,
            "artistic_style": 0.7,
            "speed": 0.3,
            "quality": 0.98,
            "consistency": 0.9,
            "editability": 0.85,
            
            "holistic_edit": 0.8,
            "localized_edit": 0.75,
            "character_consistency": 0.85,
            "pose_control": 0.6
          },
          
          "style_tags": ["photorealistic", "artistic", "editing", "character"],
          
          "notes": "All-in-one solution, excellent quality but large and slow"
        },
        
        "qwen_vl_edit": {
          "display_name": "Qwen2.5-VL Edit",
          "url": "https://...",
          "size_gb": 18.0,
          "hash_sha256": "...",
          
          "capabilities": ["edit", "i2i"],
          "model_family": "qwen",
          "has_gguf": true,
          
          "requirements": {
            "min_vram_gb": 10,
            "min_ram_gb": 24
          },
          
          "approach": "monolithic",
          "requires_nodes": ["ComfyUI-Qwen2-VL"],
          
          "scoring": {
            "photorealism": 0.85,
            "artistic_style": 0.6,
            "speed": 0.5,
            "quality": 0.9,
            "consistency": 0.8,
            "editability": 0.95,
            
            "holistic_edit": 0.95,
            "localized_edit": 0.7,
            "character_consistency": 0.6,
            "pose_control": 0.3
          },
          
          "style_tags": ["editing", "transform", "style_transfer"],
          
          "notes": "Best-in-class holistic editing, instruction-based transforms"
        }
      },
      
      "unet_gguf": {
        "wan_i2v_q5": {
          "display_name": "Wan 2.2 I2V (Q5 Quantized)",
          "files": {
            "high_noise": {
              "url": "https://huggingface.co/...",
              "size_gb": 9.8,
              "hash_sha256": "..."
            },
            "low_noise": {
              "url": "https://huggingface.co/...",
              "size_gb": 9.8,
              "hash_sha256": "..."
            }
          },
          
          "capabilities": ["i2v"],
          "model_family": "gguf",
          "is_quantized": true,
          "quantization": "Q5_K_M",
          
          "requirements": {
            "min_vram_gb": 0,
            "min_ram_gb": 32
          },
          
          "approach": "minimal",
          "requires_nodes": ["ComfyUI-GGUF", "ComfyUI-VideoHelperSuite"],
          
          "scoring": {
            "photorealism": 0.7,
            "artistic_style": 0.6,
            "speed": 0.3,
            "quality": 0.75,
            "consistency": 0.8,
            "editability": 0.1,
            
            "motion_subtlety": 0.85,
            "motion_dynamic": 0.5,
            "temporal_coherence": 0.8
          },
          
          "style_tags": ["video", "animation", "documentary", "subtle_motion"],
          
          "notes": "Optimized for Apple Silicon, excellent for documentary-style subtle animation"
        },
        
        "hunyuan_video_gguf": {
          "display_name": "HunyuanVideo (GGUF)",
          "url": "https://...",
          "size_gb": 12.5,
          "hash_sha256": "...",
          
          "capabilities": ["i2v", "t2v"],
          "model_family": "gguf",
          "is_quantized": true,
          
          "requirements": {
            "min_vram_gb": 0,
            "min_ram_gb": 48
          },
          
          "approach": "minimal",
          "requires_nodes": ["ComfyUI-GGUF", "ComfyUI-VideoHelperSuite"],
          
          "scoring": {
            "photorealism": 0.8,
            "artistic_style": 0.7,
            "speed": 0.2,
            "quality": 0.85,
            "consistency": 0.75,
            "editability": 0.1,
            
            "motion_subtlety": 0.6,
            "motion_dynamic": 0.85,
            "temporal_coherence": 0.7
          },
          
          "style_tags": ["video", "animation", "action", "dynamic_motion"],
          
          "notes": "Better for dynamic motion, longer generation times"
        }
      }
    }
  }
}
```

### 13.9 Onboarding Survey UI Flow

The survey collects data to populate `UserProfile` using **1-5 scales with visible semantic labels**.

```
┌─────────────────────────────────────────────────────────────────┐
│                    ONBOARDING SURVEY                             │
└─────────────────────────────────────────────────────────────────┘

SCREEN 1: Experience Assessment
─────────────────────────────────────────────────────────────────
"How would you rate your experience with AI image/video tools?"

 ○ Beginner      - Never used them
 ○ Novice        - Tried a few times  
 ● Intermediate  - Use regularly, understand basics
 ○ Advanced      - Power user, understand internals
 ○ Expert        - Could teach others

"How comfortable are you with technical setup?"
(Installing software, terminals, config files, troubleshooting)

 ○ Beginner      - Avoid if possible
 ● Novice        - Can follow instructions
 ○ Intermediate  - Comfortable with basics
 ○ Advanced      - Handle most issues myself
 ○ Expert        - Deep technical knowledge

─────────────────────────────────────────────────────────────────

SCREEN 2: Use Case Selection
─────────────────────────────────────────────────────────────────
"What do you want to accomplish?" (Select all that apply)

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  🖼️ Generate    │  │  ✏️ Edit        │  │  🎬 Video       │
│     Images      │  │     Images      │  │                 │
│                 │  │                 │  │                 │
│ Create images   │  │ Modify existing │  │ Animate photos, │
│ from text or    │  │ images, swap    │  │ create video    │
│ reference       │  │ elements, style │  │ from images     │
│                 │  │                 │  │                 │
│     [  ✓  ]     │  │     [  ✓  ]     │  │     [  ✓  ]     │
└─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐
│  ✍️ Writing &   │  │  🎯 Full        │
│     Coding      │  │     Workstation │
│                 │  │                 │
│ AI assistant    │  │ Everything -    │
│ for text,       │  │ configure for   │
│ code, tasks     │  │ maximum         │
│                 │  │ capability      │
│     [    ]      │  │     [    ]      │
└─────────────────┘  └─────────────────┘

─────────────────────────────────────────────────────────────────

SCREEN 3a: Content Preferences - IMAGE GENERATION
─────────────────────────────────────────────────────────────────
"For generating images, rate importance of each:"

                        Not      Nice    Moderate   Very    Critical
                     Important  to Have  Important  Import.  
                         1        2         3         4        5

Photorealistic output    ○        ○         ●         ○        ○
Artistic/stylized        ○        ○         ○         ●        ○
Fast generation          ○        ●         ○         ○        ○
Maximum quality          ○        ○         ○         ●        ○
Consistent characters    ○        ○         ○         ○        ●
Pose/composition ctrl    ○        ○         ●         ○        ○

"What styles interest you?" (Select all that apply)

[✓] Photorealistic   [ ] Anime/Manga      [✓] Portraits
[ ] Fantasy          [✓] Product shots    [ ] Architecture  
[✓] Documentary      [ ] Concept art      [ ] Landscapes

─────────────────────────────────────────────────────────────────

SCREEN 3b: Content Preferences - IMAGE EDITING
─────────────────────────────────────────────────────────────────
"For editing images, rate importance of each:"

                        Not      Nice    Moderate   Very    Critical
                     Important  to Have  Important  Import.  
                         1        2         3         4        5

Full-image transforms    ○        ○         ●         ○        ○
  (style, lighting, mood)

Targeted edits           ○        ○         ○         ●        ○
  (inpaint, remove, swap)

Keep original quality    ○        ○         ○         ○        ●

"What types of edits matter most?"

[✓] Object removal       [ ] Background swap    [✓] Style transfer
[ ] Face swap            [✓] Color grading      [ ] Upscaling

─────────────────────────────────────────────────────────────────

SCREEN 3c: Content Preferences - VIDEO GENERATION  
─────────────────────────────────────────────────────────────────
"For creating videos, rate importance of each:"

                        Not      Nice    Moderate   Very    Critical
                     Important  to Have  Important  Import.  
                         1        2         3         4        5

Smooth, coherent motion  ○        ○         ○         ●        ○
Longer clips (10s+)      ○        ●         ○         ○        ○
Fast preview generation  ○        ○         ●         ○        ○

"What type of motion fits your work?"

 ● Subtle / Documentary  - Gentle movement, photo comes alive
 ○ Moderate              - Natural motion, balanced
 ○ Dynamic / Action      - Energetic, dramatic movement

"What's your primary video use case?"

 ● Historical photo animation (documentary)
 ○ Product visualization
 ○ Social media content  
 ○ Creative/artistic exploration
 ○ Character animation

─────────────────────────────────────────────────────────────────

SCREEN 4: Setup Preferences (shown if tech_experience >= 3)
─────────────────────────────────────────────────────────────────
"How do you prefer your AI tools configured?"

                        Not      Nice    Moderate   Very    Critical
                     Important  to Have  Important  Import.  
                         1        2         3         4        5

Simple setup             ○        ○         ●         ○        ○
  (fewer parts to manage)

Run everything locally   ○        ○         ○         ●        ○
  (no cloud/API calls)

Open source models       ○        ●         ○         ○        ○
  (vs proprietary)


"For advanced capabilities, which approach do you prefer?"

 ○ Minimal - Fewest models/nodes, simplest setup
 ○ Enhanced Lightweight - Base model + specialized nodes 
     (e.g., SDXL + IPAdapter + ControlNet)
 ● Monolithic - Single powerful model does everything
     (e.g., Flux.Kontext, Qwen-Edit)  
 ○ Auto - Let the system decide based on my needs

"Accept quantized models for better compatibility?"
 [✓] Yes - Prioritize running smoothly over maximum quality

─────────────────────────────────────────────────────────────────

SCREEN 5: Review Profile
─────────────────────────────────────────────────────────────────
"Here's your profile:"

┌─────────────────────────────────────────────────────────────────┐
│ Experience Level: Intermediate                                  │
│   • AI Tools: Intermediate (3/5)                               │
│   • Technical: Novice (2/5)                                    │
├─────────────────────────────────────────────────────────────────┤
│ Selected Use Cases:                                            │
│   • Image Generation                                           │
│   • Image Editing                                              │
│   • Video Generation                                           │
├─────────────────────────────────────────────────────────────────┤
│ Top Priorities:                                                │
│   1. Character Consistency (Critical)                          │
│   2. Targeted Edits (Very Important)                           │
│   3. Photorealism (Moderate)                                   │
│   4. Smooth Motion (Very Important)                            │
├─────────────────────────────────────────────────────────────────┤
│ Style: Documentary, Photorealistic, Portraits, Product         │
│ Video Style: Subtle/Documentary motion                         │
│ Setup: Monolithic approach, quantization OK                    │
└─────────────────────────────────────────────────────────────────┘

                    [ ← Edit ]  [ Continue → ]
```

### 13.9 RecommendationService Implementation

```python
class RecommendationService:
    """
    Weighted scoring-based recommendation engine.
    """
    
    def __init__(self, resources_path: str):
        with open(resources_path) as f:
            self.resources = json.load(f)
        
        self.config = self.resources.get("recommendation_config", {})
        self.weights = self.config.get("scoring_weights", {})
        self.thresholds = self.config.get("proficiency_thresholds", {})
        self.limits = self.config.get("hard_limits", {})
    
    def generate_recommendations(
        self,
        user_profile: UserProfile,
        environment: EnvironmentReport
    ) -> RecommendationResult:
        """
        Main entry point for recommendation generation.
        """
        reasoning = []
        warnings = []
        
        # Phase 1: Normalize inputs
        hardware = HardwareConstraints.from_environment(environment)
        proficiency = self._determine_proficiency(user_profile)
        
        reasoning.append(f"Detected proficiency level: {proficiency}")
        reasoning.append(f"Hardware profile: {hardware.gpu_vendor}, "
                        f"VRAM score: {hardware.vram_score:.2f}, "
                        f"Compute score: {hardware.compute_score:.2f}")
        
        # Phase 2-3: Score candidates for each use case
        all_selections = {}
        
        for use_case in user_profile.primary_use_cases:
            content_prefs = user_profile.content_preferences.get(use_case)
            if not content_prefs:
                continue
            
            selection = self._resolve_use_case(
                use_case=use_case,
                content_prefs=content_prefs,
                hardware=hardware,
                proficiency=proficiency,
                reasoning=reasoning,
                warnings=warnings
            )
            
            all_selections[use_case] = selection
        
        # Phase 7: Generate manifest
        manifest = self._compile_manifest(all_selections, hardware, reasoning)
        
        # Phase 8: Generate output
        confidence = self._calculate_confidence(all_selections)
        
        return RecommendationResult(
            recommendation_id=str(uuid.uuid4()),
            confidence_score=confidence,
            user_profile=user_profile,
            hardware_constraints=hardware,
            selections=all_selections,
            manifest=manifest,
            reasoning=reasoning,
            warnings=warnings
        )
    
    def _determine_proficiency(self, profile: UserProfile) -> str:
        """Derive proficiency level from experience scores."""
        ai = profile.ai_experience
        tech = profile.technical_experience
        
        if ai >= 8 and tech >= 8:
            return "Expert"
        elif ai >= 7 or tech >= 7:
            return "Advanced"
        elif ai >= 4 or tech >= 4:
            return "Intermediate"
        else:
            return "Beginner"
    
    def _resolve_use_case(
        self,
        use_case: str,
        content_prefs: ContentPreferences,
        hardware: HardwareConstraints,
        proficiency: str,
        reasoning: List[str],
        warnings: List[str]
    ) -> UseCaseSelection:
        """Resolve optimal configuration for a single use case."""
        
        # Get required capabilities for this use case
        use_case_config = self.resources["use_cases"].get(use_case, {})
        required_capabilities = use_case_config.get("capabilities", [])
        
        reasoning.append(f"Resolving {use_case}: needs {required_capabilities}")
        
        # Load and score all model candidates
        candidates = self._load_model_candidates(required_capabilities)
        scored = []
        
        for candidate in candidates:
            scored_candidate = self._score_candidate(
                candidate, content_prefs, hardware
            )
            
            if scored_candidate.composite_score > 0:
                scored.append(scored_candidate)
                reasoning.append(
                    f"  {candidate.model_id}: "
                    f"user_fit={scored_candidate.user_fit_score:.2f}, "
                    f"hw_fit={scored_candidate.hardware_fit_score:.2f}, "
                    f"composite={scored_candidate.composite_score:.2f}"
                )
            else:
                reasoning.append(
                    f"  {candidate.model_id}: REJECTED (hardware incompatible)"
                )
        
        if not scored:
            warnings.append(f"No compatible models found for {use_case}")
            return UseCaseSelection(use_case=use_case, models=[], workflows=[], nodes=[])
        
        # Sort by composite score
        scored.sort(key=lambda c: c.composite_score, reverse=True)
        
        # Select best model per capability
        selected_models = self._select_best_per_capability(
            scored, required_capabilities, reasoning
        )
        
        # Find compatible workflows
        selected_workflows = self._select_workflows(
            use_case, selected_models, hardware, reasoning
        )
        
        # Collect required nodes
        required_nodes = self._collect_required_nodes(
            selected_models, selected_workflows
        )
        
        return UseCaseSelection(
            use_case=use_case,
            models=selected_models,
            workflows=selected_workflows,
            nodes=required_nodes,
            top_candidate_score=scored[0].composite_score if scored else 0
        )
    
    def _score_candidate(
        self,
        candidate: ModelCandidate,
        content_prefs: ContentPreferences,
        hardware: HardwareConstraints
    ) -> ModelCandidate:
        """Apply the scoring algorithm to a candidate."""
        
        # User fit score
        pref_values = [
            content_prefs.photorealism,
            content_prefs.artistic_style,
            content_prefs.speed,
            content_prefs.quality,
            content_prefs.consistency
        ]
        pref_sum = sum(pref_values)
        
        if pref_sum > 0:
            weights = [p / pref_sum for p in pref_values]
        else:
            weights = [0.2] * 5
        
        model_scores = [
            candidate.photorealism_score,
            candidate.artistic_score,
            candidate.speed_score,
            candidate.quality_score,
            candidate.consistency_score
        ]
        
        user_fit = sum(w * s for w, s in zip(weights, model_scores))
        
        # Style tag bonus
        model_tags = set(candidate.model_info.get("style_tags", []))
        user_tags = set(content_prefs.style_tags)
        tag_matches = len(model_tags & user_tags)
        tag_bonus = min(
            self.weights["user_fit_components"]["style_tag_max_bonus"],
            tag_matches * self.weights["user_fit_components"]["style_tag_match_bonus"]
        )
        
        candidate.user_fit_score = min(1.0, user_fit + tag_bonus)
        
        # Hardware fit score
        hw_fit = 1.0
        
        # Check hard limits
        if candidate.min_vram_gb > hardware.vram_gb:
            if hardware.requires_quantization and candidate.model_info.get("has_gguf"):
                hw_fit += self.weights["hardware_penalties"]["quantization_required"]
            else:
                hw_fit = 0.0
        
        if candidate.min_ram_gb > hardware.ram_gb:
            hw_fit = 0.0
        
        # Storage check
        max_storage_pct = self.limits.get("storage_max_usage_pct", 0.8)
        if candidate.size_gb > hardware.disk_free_gb * max_storage_pct:
            hw_fit = 0.0
        elif candidate.size_gb > hardware.disk_free_gb * 0.5:
            hw_fit += self.weights["hardware_penalties"]["storage_over_50pct"]
        
        # Speed penalty
        if hardware.compute_score < 0.5 and candidate.speed_score < 0.5:
            hw_fit += self.weights["hardware_penalties"]["slow_model_slow_hw"]
        
        candidate.hardware_fit_score = max(0.0, hw_fit)
        
        # Composite score
        if candidate.hardware_fit_score == 0.0:
            candidate.composite_score = 0.0
        else:
            hw_weight = self.weights["composite"]["hardware_fit"]
            user_weight = self.weights["composite"]["user_fit"]
            candidate.composite_score = (
                hw_weight * candidate.hardware_fit_score +
                user_weight * candidate.user_fit_score
            )
        
        return candidate
    
    def _select_best_per_capability(
        self,
        candidates: List[ModelCandidate],
        required_capabilities: List[str],
        reasoning: List[str]
    ) -> List[str]:
        """Select the best model for each required capability."""
        selected = []
        
        for capability in required_capabilities:
            best = None
            best_score = 0
            
            for candidate in candidates:
                if capability in candidate.capabilities:
                    if candidate.composite_score > best_score:
                        best = candidate
                        best_score = candidate.composite_score
            
            if best and best.model_id not in selected:
                selected.append(best.model_id)
                reasoning.append(
                    f"Selected {best.model_id} for {capability} "
                    f"(score: {best.composite_score:.2f})"
                )
        
        return selected
    
    def _calculate_confidence(self, selections: Dict[str, UseCaseSelection]) -> float:
        """Calculate overall confidence in the recommendation."""
        if not selections:
            return 0.0
        
        scores = [s.top_candidate_score for s in selections.values() if s.top_candidate_score > 0]
        
        if not scores:
            return 0.0
        
        return sum(scores) / len(scores)
```

### 13.10 Output Schema

```python
@dataclass
class RecommendationResult:
    """Complete output of the recommendation engine."""
    
    recommendation_id: str
    confidence_score: float             # 0-1, overall confidence
    
    # Inputs (for reference/debugging)
    user_profile: UserProfile
    hardware_constraints: HardwareConstraints
    
    # Selections per use case
    selections: Dict[str, UseCaseSelection]
    
    # Installation manifest
    manifest: InstallationManifest
    
    # Explanations
    reasoning: List[str]                # Why each decision was made
    warnings: List[str]                 # Potential issues


@dataclass
class UseCaseSelection:
    """Selection for a single use case."""
    
    use_case: str
    models: List[str]                   # Model IDs to install
    workflows: List[str]                # Workflow IDs to install
    nodes: List[str]                    # Custom node IDs required
    top_candidate_score: float          # Score of best candidate


@dataclass  
class InstallationManifest:
    """Complete installation specification."""
    
    # Models to download
    models: List[ModelDownload]
    
    # Custom nodes to clone
    nodes: List[NodeInstall]
    
    # Workflows to copy
    workflows: List[WorkflowInstall]
    
    # Totals
    total_size_gb: float
    estimated_time_minutes: int


@dataclass
class ModelDownload:
    """Single model download specification."""
    
    model_id: str
    url: str
    dest_path: str                      # Relative to ComfyUI/models/
    size_gb: float
    hash_sha256: str
    is_quantized: bool
```
```

---

## 14. Updated File Structure

### 14.1 Complete New File List

```
src/
├── services/
│   ├── setup_wizard_service.py        # NEW: Wizard orchestration
│   ├── shortcut_service.py            # NEW: Desktop shortcut creation
│   ├── download_service.py            # NEW: Download with retry/progress
│   ├── model_manager_service.py       # NEW: Local model management
│   ├── model_repository_service.py    # NEW: External repo integration
│   ├── workflow_service.py            # NEW: Workflow management
│   ├── recommendation_service.py      # EXISTS: Enhance with resolver
│   ├── comfy_service.py               # EXISTS: Enhance
│   ├── dev_service.py                 # EXISTS: Enhance
│   └── system_service.py              # EXISTS: Fix + enhance
│
├── ui/
│   ├── wizard/
│   │   ├── __init__.py
│   │   ├── setup_wizard.py            # NEW: Main wizard window
│   │   └── components/
│   │       ├── __init__.py
│   │       ├── use_case_card.py       # NEW
│   │       ├── module_config.py       # NEW
│   │       ├── api_key_input.py       # NEW
│   │       ├── progress_panel.py      # NEW
│   │       ├── reasoning_display.py   # NEW
│   │       └── warning_banner.py      # NEW
│   │
│   └── views/
│       ├── model_manager.py           # NEW: Model management view
│       ├── workflow_browser.py        # NEW: Workflow browser view
│       ├── overview.py                # EXISTS: Update
│       ├── comfyui.py                 # EXISTS: Fix + update
│       ├── devtools.py                # EXISTS: Update
│       └── settings.py                # EXISTS: Update
│
├── config/
│   └── resources.json                 # EXISTS: Major update
│
└── workflows/                          # NEW: Bundled workflow templates
    ├── wan_i2v_basic.json
    ├── sdxl_basic_t2i.json
    ├── flux_schnell_t2i.json
    └── previews/
        ├── wan_i2v_basic.png
        ├── sdxl_basic_t2i.png
        └── flux_schnell_t2i.png
```

### 14.2 Updated Implementation Phases

| Phase | Focus | Files | Priority |
|-------|-------|-------|----------|
| 1 | Critical Fixes | system_service.py, comfyui.py | BLOCKER |
| 2 | GGUF + Video | resources.json, comfy_service.py, workflows/ | HIGH |
| 3 | Core Services | shortcut_service.py, download_service.py, setup_wizard_service.py | HIGH |
| 4 | Wizard UI | wizard/*.py | HIGH |
| 5 | Model Manager | model_manager_service.py, model_repository_service.py, model_manager.py | MEDIUM |
| 6 | Workflow Browser | workflow_service.py, workflow_browser.py | MEDIUM |
| 7 | Polish | All views, error handling, testing | MEDIUM |
| 8 | Future Modules | LM Studio, MCP | LOW |

---

*End of Specification*
