# ComfyUI Mac Installer

A robust, automated installer for [ComfyUI](https://github.com/comfyanonymous/ComfyUI) specifically designed for macOS (Apple Silicon M1/M2/M3 & Intel). 

This script handles the entire setup process, ensuring a clean, isolated environment with the correct dependencies for optimal performance on Mac.

## Features

- **🍏 Apple Silicon Optimized:** Automatically detects M-series chips and installs PyTorch with MPS (Metal Performance Shaders) support for GPU acceleration.
- **📂 Interactive Install Location:** Uses a native macOS Finder dialog to let you choose exactly where to install ComfyUI.
- **🛡️ Isolated Environment:** Sets up a dedicated Python `venv` so it doesn't mess with your system Python.
- **📦 Dependency Management:** Checks for and installs Homebrew, Python 3.10, Git, and all required Python packages.
- **🚀 One-Click Launcher:** Creates a clickable `.command` file on your Desktop to launch ComfyUI instantly.
- **🔧 ComfyUI Manager:** Automatically installs [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager) for easy node installation.

## Usage

1.  **Download the script** (`install_comfyui_mac.sh`) to your Mac.
2.  Open your **Terminal** app.
3.  Navigate to the download location and make the script executable:
    ```bash
    cd ~/Downloads
    chmod +x install_comfyui_mac.sh
    ```
4.  **Run the script:**
    ```bash
    ./install_comfyui_mac.sh
    ```
5.  Follow the prompts to select your install folder.
6.  Once finished, use the **Run_ComfyUI.command** shortcut on your Desktop to start the application.

## Requirements

- macOS (12.0+ recommended for best MPS support)
- Internet connection (for downloading dependencies)
