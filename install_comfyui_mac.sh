#!/bin/bash

# ==============================================================================
# ComfyUI GUI Installer for macOS
# ==============================================================================

# --- Configuration & Defaults ---
COMFY_REPO_URL="https://github.com/comfyanonymous/ComfyUI.git"
MANAGER_REPO_URL="https://github.com/ltdrdata/ComfyUI-Manager.git"
IMPACT_PACK_REPO_URL="https://github.com/ltdrdata/ComfyUI-Impact-Pack.git"
GGUF_REPO_URL="https://github.com/city96/ComfyUI-GGUF.git"
PYTHON_VERSION="python@3.10"

# --- Helper: AppleScript Wrappers ---
osascript_cmd() {
    osascript -e "$1" 2>/dev/null
}

show_alert() {
    osascript_cmd "display dialog \"$1\" buttons {\"OK\"} default button \"OK\" with icon note with title \"ComfyUI Installer\""
}

ask_confirmation() {
    RESULT=$(osascript_cmd "display dialog \"$1\" buttons {\"Cancel\", \"$2\"} default button \"$2\" with icon caution with title \"ComfyUI Installer\"")
    if [[ "$RESULT" != *"button returned:$2"* ]]; then
        echo "User Cancelled."
        exit 0
    fi
}

send_notification() {
    osascript_cmd "display notification \"$1\" with title \"ComfyUI Installer\""
}

# --- Helper: Progress Bar ---
# Usage: progress_bar <current_step> <total_steps> <description>
progress_bar() {
    local current=$1
    local total=$2
    local task=$3
    local width=30
    local percent=$((current * 100 / total))
    local filled=$((percent * width / 100))
    local empty=$((width - filled))

    # Clear line
    printf "\r\033[K"
    
    # Draw Bar: [====>      ] 40% - Task Description
    printf "["
    if [ $filled -gt 0 ]; then printf "%0.s=" $(seq 1 $filled); fi
    if [ $filled -lt $width ]; then printf ">"; fi
    if [ $empty -gt 1 ]; then printf "%0.s " $(seq 1 $((empty - 1))); fi
    printf "] %3d%% - %s" "$percent" "$task"
}

# --- 1. Welcome Screen ---
clear
echo "==========================================