# ComfyUI Universal Dashboard

A cross-platform (Windows, macOS, Linux) installer and management dashboard for [ComfyUI](https://github.com/comfyanonymous/ComfyUI).

## 🚀 Quick Start

Download this repository, unzip it, and double-click the file for your system:

| Operating System | File to Double-Click |
| :--- | :--- |
| **Windows** | **`Run_Windows.bat`** |
| **macOS** | **`Run_Mac.command`** |
| **Linux** | **`Run_Linux.sh`** |

## 🍎 macOS Troubleshooting
If you see a message saying **"Apple could not verify..."** or **"Moved to Trash"**:

**Option 1: Privacy Settings**
1.  Open **System Settings** -> **Privacy & Security**.
2.  Scroll down to the "Security" section.
3.  Click **"Open Anyway"** next to the message about `Run_Mac.command`.

**Option 2: Terminal Fix (Guaranteed)**
1.  Open **Terminal**.
2.  Run this command (replace path with your actual file location):
    ```bash
    xattr -d com.apple.quarantine ~/Downloads/ComfyUI-Universal-Dashboard/Run_Mac.command
    ```
    *(Tip: Type `xattr -d com.apple.quarantine ` then drag the file into the window).*

## Features

- **🖥️ Universal Dashboard:** A beautiful GUI that works on all operating systems.
- **🚀 One-Click Install:** Automatically sets up Python, Virtual Environment, and Git.
- **🧠 Smart Detection:** 
    - **Windows:** Detects NVIDIA GPUs and installs CUDA-enabled PyTorch.
    - **macOS:** Installs Metal (MPS) optimized PyTorch for Apple Silicon.
- **⚡ Management:** Install Manager, Download Models, and Update with one click.
- **🧪 Smoke Test:** Verifies the server actually starts and responds.
- **🔧 Dev Tools:** Install Node.js and AI CLIs (Claude, Gemini, etc.) easily.

## Requirements

- **Internet Connection**
- **Windows:** Python 3.10+ (Check "Add to PATH" during install)
- **macOS:** Homebrew (The script will attempt to install it if missing)
- **Linux:** `python3-venv`, `python3-pip`, `git`, `python3-tk`
