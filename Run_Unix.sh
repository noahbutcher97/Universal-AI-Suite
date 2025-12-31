#!/bin/bash

# Ensure we run from the script directory
cd "$(dirname "$0")"

echo "=== AI Universal Suite Launcher ==="

# 1. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found."
    
    # Try to detect OS and offer help
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt &> /dev/null; then
            echo "[INIT] Detected Debian/Ubuntu. Attempting install..."
            sudo apt update && sudo apt install -y python3 python3-venv python3-pip
        elif command -v dnf &> /dev/null; then
            echo "[INIT] Detected Fedora. Attempting install..."
            sudo dnf install -y python3
        else
            echo "Please install Python 3.10+ manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Please install Python 3 using brew: brew install python3"
        echo "Or download from python.org"
        exit 1
    fi
fi

# 2. Check for Git
if ! command -v git &> /dev/null; then
    echo "[WARN] Git not found. Some features may fail."
fi

# 3. Launch Universal Script
echo "[INFO] Handing over to Python launcher..."
python3 launch.py

# Pause on exit if error
if [ $? -ne 0 ]; then
    echo "[ERROR] Launcher exited with error."
    read -p "Press enter to close..."
fi
