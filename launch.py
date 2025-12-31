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
import logging
from logging.handlers import RotatingFileHandler
import shutil
import time

# Configuration
MIN_PYTHON = (3, 10)
APP_NAME = "AI Universal Suite"
LOG_FILENAME = "launcher.log"

# Setup Logging
def setup_logging():
    """Configures logging to file and console."""
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # File Handler
    file_handler = RotatingFileHandler(LOG_FILENAME, maxBytes=1024*1024, backupCount=5)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )

def check_python_version():
    """Ensures Python version is sufficient."""
    if sys.version_info < MIN_PYTHON:
        logging.error(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required.")
        logging.error(f"Current version: {sys.version}")
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
        logging.info(f"Creating virtual environment in {paths['venv']}...")
        try:
            subprocess.check_call([sys.executable, "-m", "venv", paths["venv"]])
        except subprocess.CalledProcessError:
            logging.error("Failed to create virtual environment.")
            sys.exit(1)
    
    # Verify python exists in venv
    if not os.path.exists(paths["python"]):
        # Unix fallback: sometimes it's 'python' not 'python3' inside venv
        if platform.system() != "Windows":
             alt_path = paths["python"].replace("python3", "python")
             if os.path.exists(alt_path):
                 return alt_path
        
        logging.error(f"Virtual environment python not found at {paths['python']}")
        sys.exit(1)
        
    return paths["python"]

def install_deps(pip_path, root_dir):
    """Installs requirements from requirements.txt."""
    req_file = os.path.join(root_dir, "requirements.txt")
    
    if not os.path.exists(req_file):
        logging.error(f"requirements.txt not found at {req_file}")
        sys.exit(1)

    logging.info("Installing/Verifying dependencies...")
    
    # Use subprocess to stream output to logger? 
    # For now, just let it print to stdout so user sees progress, but wrap in try/catch
    cmd = [pip_path, "install", "-r", req_file]
    
    try:
        # We assume pip output is useful for the user
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to install dependencies from {req_file}.")
        logging.error(f"Pip exited with status {e.returncode}")
        sys.exit(1)

def launch_app(python_path, root_dir):
    """Launches the main app."""
    main_script = os.path.join(root_dir, "src", "main.py")
    logging.info(f"Launching {APP_NAME}...")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = root_dir
    
    # Ensure stdout flush for logging
    sys.stdout.flush()
    
    try:
        # We delegate execution to the venv python
        # We don't capture output here to allow app to control console, 
        # but the app itself (src/utils/logger.py) should handle its own logging.
        subprocess.call([python_path, main_script], env=env)
    except KeyboardInterrupt:
        logging.info("Exiting...")
    except Exception as e:
        logging.error(f"Application crashed: {e}")

def check_system_dependencies():
    """Checks for essential external tools like git."""
    if not shutil.which("git"):
        logging.warning("Git is not found in PATH. Some features (cloning repositories) will fail.")
        # We don't exit, but we warn.

def main():
    setup_logging()
    
    try:
        logging.info("--- Launcher Started ---")
        check_python_version()
        check_system_dependencies()
        
        paths = get_env_paths()
        
        # Ensure .dashboard_env exists
        if not os.path.exists(paths["env"]):
            os.makedirs(paths["env"])
            
        venv_python = setup_venv(paths)
        
        # Normalize pip path if python path changed (Unix fallback)
        if platform.system() != "Windows" and "python3" not in os.path.basename(venv_python):
            pip_path = os.path.join(os.path.dirname(venv_python), "pip")
        else:
            pip_path = paths["pip"]
            
        install_deps(pip_path, paths["root"])
        launch_app(venv_python, paths["root"])
        
    except Exception as e:
        logging.critical(f"Unhandled exception in launcher: {e}", exc_info=True)
        print("An unexpected error occurred. Check launcher.log for details.")
        if platform.system() == "Windows":
            os.system("pause")
        sys.exit(1)

if __name__ == "__main__":
    main()