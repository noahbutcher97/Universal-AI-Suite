#!/bin/bash

# ==============================================================================
# ComfyUI System Dashboard - Bootstrap Script
# ==============================================================================

echo "Initializing Dashboard..."

# 1. Ensure Homebrew
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ARCH_NAME="$(uname -m)"
    if [[ "$ARCH_NAME" == "arm64" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        eval "$(/usr/local/bin/brew shellenv)"
    fi
fi

# 2. Ensure Python 3.10+
if ! command -v python3 &> /dev/null; then
    echo "Installing Python..."
    brew install python@3.10
fi

# 3. Create a mini-venv for the Dashboard itself (separate from ComfyUI)
DASHBOARD_DIR="$HOME/.comfy_dashboard_tools"
mkdir -p "$DASHBOARD_DIR"

if [ ! -d "$DASHBOARD_DIR/venv" ]; then
    echo "Setting up Dashboard tools..."
    python3 -m venv "$DASHBOARD_DIR/venv"
fi

source "$DASHBOARD_DIR/venv/bin/activate"

# 4. Install Dashboard Libraries (Rich, psutil)
# Quietly install unless there's an error
pip install rich psutil >/dev/null 2>&1

# 5. Run the Dashboard
# We assume dashboard.py is in the same folder as this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
python3 "$SCRIPT_DIR/dashboard.py"
