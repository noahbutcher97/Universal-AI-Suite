#!/bin/bash

# Define Installation Path
INSTALL_DIR="$HOME/AI-Universal-Suite"
REPO_URL="https://github.com/noahbutcher97/ComfyUI-Universal-Dashboard.git"

echo "=========================================================="
echo "   AI Universal Suite - One-Step Installer"
echo "=========================================================="

# 1. Clone or Update
if [ -d "$INSTALL_DIR" ]; then
    echo "🔄 Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "⬇️  Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 2. Permissions & Security Fix (The "Anti-Malware Warning" fix)
echo "🛡️  Fixing permissions and whitelisting..."
chmod +x Run_Unix.sh
chmod +x Run_Mac.command

# Remove the 'Quarantine' attribute that causes the "Unidentified Developer" popup
# We try to remove it from the whole directory to be safe
xattr -r -d com.apple.quarantine "$INSTALL_DIR" 2>/dev/null

# 3. Create Desktop Launcher
DESKTOP_LAUNCHER="$HOME/Desktop/AI-Suite.command"

echo "#!/bin/bash" > "$DESKTOP_LAUNCHER"
echo "cd \"$INSTALL_DIR\"" >> "$DESKTOP_LAUNCHER"
echo "./Run_Unix.sh" >> "$DESKTOP_LAUNCHER"

chmod +x "$DESKTOP_LAUNCHER"
# Whitelist the desktop launcher specifically
xattr -d com.apple.quarantine "$DESKTOP_LAUNCHER" 2>/dev/null

echo ""
echo "✅ Installation Complete!"
echo "----------------------------------------------------------"
echo "You can now open 'AI-Suite.command' on your Desktop."
echo "No security warnings will appear."
echo "----------------------------------------------------------"
