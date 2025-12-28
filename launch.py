#!/usr/bin/env python3
"""
Universal Launcher for AI Universal Suite
Handles environment detection, virtual env creation, dependency installation, and app launch.
Works on Windows, macOS, and Linux.
"""
import sys
import os
import subprocess
import platform
import shutil

# Minimum Python version required
MIN_PYTHON = (3, 10)

def check_python_version():
    if sys.version_info < MIN_PYTHON:
        print(f"Error: Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required.")
        print(f"Current version: {sys.version}")
        sys.exit(1)

def get_env_paths():
    """Returns dict with paths for venv, python, pip based on OS."""
    root_dir = os.path.dirname(os.path.abspath(__file__))
    env_dir = os.path.join(root_dir, ".dashboard_env")
    venv_dir = os.path.join(env_dir, "venv")
    
    is_win = platform.system() == "Windows"
    
    if is_win:
        python_bin = os.path.join(venv_dir, "Scripts", "python.exe")
        pip_bin = os.path.join(venv_dir, "Scripts", "pip.exe")
    else:
        python_bin = os.path.join(venv_dir, "bin", "python3")
        pip_bin = os.path.join(venv_dir, "bin", "pip")
        
    return {
        "root": root_dir,
        "env": env_dir,
        "venv": venv_dir,
        "python": python_bin,
        "pip": pip_bin
    }

def setup_venv(paths):
    """Creates venv if missing."""
    if not os.path.exists(paths["venv"]):
        print(f"[INIT] Creating virtual environment in {paths['venv']}...")
        try:
            subprocess.check_call([sys.executable, "-m", "venv", paths["venv"]])
        except subprocess.CalledProcessError:
            print("Error: Failed to create virtual environment.")
            sys.exit(1)
    
    # Verify python exists in venv
    if not os.path.exists(paths["python"]):
        print(f"Error: Virtual environment python not found at {paths['python']}")
        # Fallback for unix sometimes calling it python instead of python3
        if platform.system() != "Windows":
             alt_path = paths["python"].replace("python3", "python")
             if os.path.exists(alt_path):
                 return alt_path
        sys.exit(1)
        
    return paths["python"]

def install_deps(pip_path):
    """Installs requirements from requirements.txt."""
    print("[INIT] Installing dependencies...")
    req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "requirements.txt")
    
    if not os.path.exists(req_file):
        print(f"FATAL: requirements.txt not found at {req_file}")
        sys.exit(1)

    cmd = [pip_path, "install", "-r", req_file, "--quiet"]
        
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f"FATAL: Failed to install dependencies from {req_file}.")
        print(f"Pip exited with status {e.returncode}")
        sys.exit(1)

def launch_app(python_path, root_dir):
    """Launches the main app."""
    main_script = os.path.join(root_dir, "src", "main.py")
    print(f"[INFO] Launching AI Universal Suite...")
    
    # Flush stdout before replacing process or calling subprocess
    sys.stdout.flush()
    
    env = os.environ.copy()
    env["PYTHONPATH"] = root_dir
    
    try:
        subprocess.call([python_path, main_script], env=env)
    except KeyboardInterrupt:
        print("\nExiting...")

def main():
    # #TODO: Add a pre-flight check for essential system dependencies.
    # The application relies on 'git' for cloning repositories, but there is
    # no check to ensure it's installed and available in the system's PATH.
    # This can lead to silent failures or cryptic errors during the ComfyUI
    # installation process.
    #
    # Suggested implementation:
    # 1. Create a function `check_system_dependencies()`.
    # 2. Inside this function, use `shutil.which('git')` to check for git.
    # 3. If git is not found, display a user-friendly error message in the
    #    console and, if possible, a graphical message box, then exit.
    # 4. Call this function at the start of `main()`.
    #
    # Example:
    #   if not shutil.which("git"):
    #       print("FATAL: Git is not installed or not in your PATH.")
    #       # Show messagebox here if tkinter is available
    #       sys.exit(1)

    check_python_version()
    paths = get_env_paths()
    
    # Ensure .dashboard_env exists
    if not os.path.exists(paths["env"]):
        os.makedirs(paths["env"])
        
    venv_python = setup_venv(paths)
    
    # Normalize pip path if python path changed (Unix fallback)
    if platform.system() != "Windows":
        pip_path = os.path.join(os.path.dirname(venv_python), "pip")
    else:
        pip_path = paths["pip"]
        
    # #TODO: Enhance user feedback during dependency installation.
    # The current `install_deps` function uses `--quiet` which suppresses
    # most of the output from pip. While this keeps the console clean, it
    # provides no feedback to the user, especially on the first run when
    # dependencies are being downloaded and installed, which can take time.
    #
    # Suggested implementation:
    # 1. Remove the `--quiet` flag from the pip command.
    # 2. Consider adding a simple visual indicator like printing dots (...)
    #    in a loop in a separate thread while the subprocess runs to show
    #    that the application has not frozen.
    install_deps(pip_path)
    launch_app(venv_python, paths["root"])

if __name__ == "__main__":
    main()
