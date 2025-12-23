import os
import sys
import time
import shutil
import subprocess
import platform
import psutil
import webbrowser
import json
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.prompt import Prompt, Confirm

# --- Global Context ---
CONSOLE = Console()
OS_SYSTEM = platform.system()
IS_WINDOWS = OS_SYSTEM == "Windows"
IS_MAC = OS_SYSTEM == "Darwin"

# --- Config & State ---
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".comfy_dashboard")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
REPO_URL = "https://github.com/comfyanonymous/ComfyUI.git"
MANAGER_URL = "https://github.com/ltdrdata/ComfyUI-Manager.git"

# Default Config
DEFAULT_CONFIG = {
    "install_path": os.path.join(os.path.expanduser("~"), "ComfyUI"),
    "auto_launch": False
}

def load_config():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

CONFIG = load_config()
INSTALL_DIR = CONFIG["install_path"]

# --- Platform Handler ---
class PlatformHandler:
    @staticmethod
    def get_venv_python():
        if IS_WINDOWS:
            return os.path.join(INSTALL_DIR, "venv", "Scripts", "python.exe")
        return os.path.join(INSTALL_DIR, "venv", "bin", "python")

    @staticmethod
    def get_venv_pip():
        if IS_WINDOWS:
            return os.path.join(INSTALL_DIR, "venv", "Scripts", "pip.exe")
        return os.path.join(INSTALL_DIR, "venv", "bin", "pip")

    @staticmethod
    def open_folder(path):
        if IS_WINDOWS:
            os.startfile(path)
        elif IS_MAC:
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])

    @staticmethod
    def has_nvidia_gpu():
        return shutil.which("nvidia-smi") is not None

# --- Core Logic ---

def get_system_metrics():
    try:
        cpu = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory().percent
        # FIX: Ensure dot is present
        disk = psutil.disk_usage(INSTALL_DIR if os.path.exists(INSTALL_DIR) else os.path.expanduser("~")).percent
        return cpu, memory, disk
    except:
        return 0, 0, 0

def is_installed():
    return os.path.exists(os.path.join(INSTALL_DIR, "main.py"))

def check_health():
    node_status = "Installed" if shutil.which("node") else "[bold red]Missing[/]"
    
    health = {
        "OS": f"{OS_SYSTEM} {platform.release()}",
        "Install Path": f"[blue]{INSTALL_DIR}[/blue]",
        "ComfyUI": "Installed" if is_installed() else "[yellow]Not Found[/yellow]",
        "Venv": "OK" if os.path.exists(os.path.dirname(PlatformHandler.get_venv_python())) else "Missing",
        "Node.js": node_status
    }
    return health

def run_cmd(cmd_list, cwd=None):
    try:
        subprocess.check_call(cmd_list, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

# --- Actions ---

def change_install_path():
    CONSOLE.print(Panel("[bold cyan]Configure Installation Path[/]", title="Settings"))
    CONSOLE.print(f"Current Path: [blue]{INSTALL_DIR}[/blue]")
    CONSOLE.print("\nEnter the full path to your ComfyUI folder (or where you want to install it).")
    CONSOLE.print("[dim]Example: D:\\AI\\ComfyUI[/]")
    
    new_path = Prompt.ask("New Path").strip().strip('"') # Remove quotes if user pasted path
    if new_path:
        CONFIG["install_path"] = new_path
        save_config(CONFIG)
        global INSTALL_DIR
        INSTALL_DIR = new_path
        CONSOLE.print("[green]Path updated! Reloading...[/]")
        time.sleep(1)

def install_node():
    CONSOLE.print(Panel("[bold cyan]Installing Node.js...[/]", title="Node.js Setup"))
    if shutil.which("node"):
        CONSOLE.print("[green]Node.js is already installed![/]")
        time.sleep(1); return

    if IS_MAC:
        run_cmd(["brew", "install", "node"])
    elif IS_WINDOWS:
        run_cmd(["winget", "install", "-e", "--id", "OpenJS.NodeJS"])
    else:
        CONSOLE.print("[yellow]Please install 'nodejs' and 'npm' via your package manager.[/]")
    time.sleep(2)

def install_torch(progress_task, progress_obj):
    pip_cmd = PlatformHandler.get_venv_pip()
    cmd = [pip_cmd, "install", "torch", "torchvision", "torchaudio"]
    
    if IS_WINDOWS or OS_SYSTEM == "Linux":
        if PlatformHandler.has_nvidia_gpu():
            progress_obj.update(progress_task, description="[cyan]GPU Detected. Installing CUDA 12.1 Torch...[/]")
            cmd.extend(["--index-url", "https://download.pytorch.org/whl/cu121"])
        else:
            progress_obj.update(progress_task, description="[yellow]No GPU. Installing CPU Torch...[/]")
    elif IS_MAC:
        progress_obj.update(progress_task, description="[cyan]macOS. Installing MPS Torch...[/]")
    
    run_cmd(cmd, cwd=INSTALL_DIR)

def run_installation():
    CONSOLE.clear()
    CONSOLE.print(Panel("[bold green]Installing ComfyUI (Clean Install)...[/]", title="Installer"))
    
    if os.path.exists(INSTALL_DIR) and os.listdir(INSTALL_DIR):
        if not Confirm.ask(f"[red]Directory {INSTALL_DIR} is not empty. Continue?[/]"):
            return

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(), TextColumn("{task.percentage:>3.0f}%")) as progress:
        task = progress.add_task("[cyan]Cloning Repo...", total=100)
        
        if not os.path.exists(INSTALL_DIR):
            run_cmd(["git", "clone", REPO_URL, INSTALL_DIR])
        progress.update(task, completed=25, description="[cyan]Creating Venv...")
        
        run_cmd([sys.executable, "-m", "venv", "venv"], cwd=INSTALL_DIR)
        progress.update(task, completed=50, description="[cyan]Installing Dependencies...")
        
        run_cmd([PlatformHandler.get_venv_pip(), "install", "--upgrade", "pip"], cwd=INSTALL_DIR)
        install_torch(task, progress)
        run_cmd([PlatformHandler.get_venv_pip(), "install", "-r", "requirements.txt"], cwd=INSTALL_DIR)
        
        progress.update(task, completed=75, description="[cyan]Installing Manager...")
        custom_nodes = os.path.join(INSTALL_DIR, "custom_nodes")
        os.makedirs(custom_nodes, exist_ok=True)
        run_cmd(["git", "clone", MANAGER_URL], cwd=custom_nodes)
        progress.update(task, completed=100)

    CONSOLE.print("[bold green]Install Complete![/]")
    time.sleep(2)

def update_comfyui():
    CONSOLE.clear()
    CONSOLE.print(Panel("[bold yellow]Updating ComfyUI...[/]", title="Updater"))
    
    if not is_installed():
        CONSOLE.print("[red]ComfyUI not found. Please Install first.[/]")
        time.sleep(2); return

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(), TextColumn("{task.percentage:>3.0f}%")) as progress:
        task = progress.add_task("[cyan]Pulling latest changes...", total=100)
        
        # Git Pull
        run_cmd(["git", "pull"], cwd=INSTALL_DIR)
        progress.update(task, completed=50, description="[cyan]Updating Requirements...")
        
        # Pip Install
        run_cmd([PlatformHandler.get_venv_pip(), "install", "-r", "requirements.txt"], cwd=INSTALL_DIR)
        progress.update(task, completed=100)
        
    CONSOLE.print("[bold green]Update Complete![/]")
    time.sleep(2)

def smoke_test():
    CONSOLE.clear()
    CONSOLE.print(Panel("[bold cyan]Running Smoke Test...[/]", title="Diagnostics"))
    
    if not is_installed():
        CONSOLE.print("[red]Not installed.[/]")
        time.sleep(1); return

    python_exec = PlatformHandler.get_venv_python()
    CONSOLE.print("[dim]Starting server on port 8199 (test mode)...[/]")
    
    cmd = [python_exec, "main.py", "--port", "8199", "--cpu"]
    
    try:
        proc = subprocess.Popen(cmd, cwd=INSTALL_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import urllib.request
        success = False
        for i in range(15):
            time.sleep(1)
            try:
                if urllib.request.urlopen("http://127.0.0.1:8199").getcode() == 200:
                    success = True; break
            except: pass
        proc.terminate()
        
        if success: CONSOLE.print(Panel("[bold green]PASS: Server responded![/]"), border_style="green")
        else: CONSOLE.print(Panel("[bold red]FAIL: No response.[/]"), border_style="red")
    except Exception as e:
        CONSOLE.print(f"[bold red]Error: {e}[/]")
    
    Prompt.ask("Press Enter to return")

def launch_app():
    if not is_installed():
        CONSOLE.print("[red]Not installed![/]"); time.sleep(1); return
    
    args = ["--auto-launch"]
    if IS_MAC: args.append("--force-fp16")
    
    subprocess.Popen([PlatformHandler.get_venv_python(), "main.py"] + args, cwd=INSTALL_DIR)
    CONSOLE.print("[green]Launched![/]"); time.sleep(2)

# --- UI Layout ---

def main():
    while True:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="stats", size=6),
            Layout(name="menu")
        )

        # Header
        grid = Table.grid(expand=True)
        grid.add_column(justify="left")
        grid.add_column(justify="right")
        grid.add_row(
            "[b magenta]ComfyUI Universal Dashboard[/b magenta]", 
            f"[dim]{OS_SYSTEM}[/dim]"
        )
        layout["header"].update(Panel(grid, style="white on blue"))

        # Stats & Health Combined
        cpu, ram, disk = get_system_metrics()
        health = check_health()
        
        t_stats = Table(expand=True, box=None)
        t_stats.add_column("System Metrics", justify="center")
        t_stats.add_column("Component Health", justify="center")
        
        t_sys = Table(show_header=False, box=None)
        t_sys.add_row("CPU", f"{cpu}%")
        t_sys.add_row("RAM", f"{ram}%")
        t_sys.add_row("Disk", f"{disk}%")
        
        t_hlth = Table(show_header=False, box=None)
        t_hlth.add_row("Install Path", health["Install Path"])
        t_hlth.add_row("ComfyUI", health["ComfyUI"])
        t_hlth.add_row("Node.js", health["Node.js"])
        
        t_stats.add_row(t_sys, t_hlth)
        layout["stats"].update(Panel(t_stats, title="Overview", border_style="blue"))

        # Menu (Grid Layout for visibility)
        menu_grid = Table(expand=True, box=None, show_header=True)
        menu_grid.add_column("Installation", style="cyan")
        menu_grid.add_column("Management", style="yellow")
        menu_grid.add_column("System", style="white")
        
        menu_grid.add_row(
            "[1] Install (Clean)", 
            "[3] Install Node.js", 
            "[5] Open Folder"
        )
        menu_grid.add_row(
            "[2] Update (Git Pull)", 
            "[4] Smoke Test", 
            "[6] Settings (Change Path)"
        )
        menu_grid.add_row(
            "", 
            "", 
            "[7] Launch ComfyUI"
        )
        
        layout["menu"].update(Panel(menu_grid, title="Actions", border_style="white"))
        
        CONSOLE.clear()
        CONSOLE.print(layout)
        
        choice = Prompt.ask("Select Option", choices=["1", "2", "3", "4", "5", "6", "7", "q", "Q"], default="q")
        
        if choice.lower() == "q": break
        if choice == "1": run_installation()
        if choice == "2": update_comfyui()
        if choice == "3": install_node()
        if choice == "4": smoke_test()
        if choice == "5": PlatformHandler.open_folder(INSTALL_DIR)
        if choice == "6": change_install_path()
        if choice == "7": launch_app()

if __name__ == "__main__":
    try: main() 
    except KeyboardInterrupt: pass
