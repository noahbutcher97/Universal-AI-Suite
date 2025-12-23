import os
import sys
import time
import shutil
import subprocess
import platform
import threading
import psutil
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.text import Text
from rich.prompt import Prompt, Confirm

# --- Configuration ---
INSTALL_DIR = os.path.expanduser("~/ComfyUI")
REPO_URL = "https://github.com/comfyanonymous/ComfyUI.git"
MANAGER_URL = "https://github.com/ltdrdata/ComfyUI-Manager.git"

console = Console()

# --- Helper Functions ---

def get_system_metrics():
    cpu = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(os.path.expanduser("~"))
    return cpu, memory.percent, disk.percent

def is_installed():
    return os.path.exists(os.path.join(INSTALL_DIR, "main.py"))

def check_health():
    """Returns a dict of component status"""
    health = {
        "Python": "OK" if sys.version_info >= (3, 10) else "Outdated",
        "Git": "OK" if shutil.which("git") else "Missing",
        "ComfyUI": "Installed" if is_installed() else "Not Found",
        "Venv": "OK" if os.path.exists(os.path.join(INSTALL_DIR, "venv")) else "Missing"
    }
    return health

def run_command(cmd, shell=True, cwd=None):
    try:
        subprocess.check_call(cmd, shell=shell, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

# --- UI Components ---

def generate_header():
    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    grid.add_row(
        "[b magenta]ComfyUI System Dashboard[/b magenta]", 
        f"[dim]{platform.system()} {platform.release()} | {platform.machine()}[/dim]"
    )
    return Panel(grid, style="white on blue")

def generate_stats():
    cpu, ram, disk = get_system_metrics()
    
    table = Table(title="System Metrics", expand=True, border_style="dim")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    
    table.add_row("CPU Usage", f"{cpu}%")
    table.add_row("RAM Usage", f"{ram}%")
    table.add_row("Disk Usage", f"{disk}%")
    
    return Panel(table, title="Real-time Stats", border_style="blue")

def generate_health_panel():
    health = check_health()
    table = Table(title="Component Health", expand=True, border_style="dim")
    table.add_column("Component")
    table.add_column("Status")
    
    for k, v in health.items():
        color = "green" if v in ["OK", "Installed"] else "red"
        table.add_row(k, f"[{color}]{v}[/{color}]")
        
    return Panel(table, title="Health Check", border_style="green")

def generate_menu():
    table = Table(title="Actions", expand=True, show_header=False, border_style="dim")
    table.add_row("[1] [bold green]Install / Repair ComfyUI[/]")
    table.add_row("[2] [bold yellow]Update ComfyUI & Manager[/]")
    table.add_row("[3] [bold cyan]Smoke Test (Verify Install)[/]")
    table.add_row("[4] [bold blue]Download Models[/]")
    table.add_row("[5] [bold white]Launch ComfyUI[/]")
    table.add_row("[Q] [bold red]Quit[/]")
    return Panel(table, title="Control Panel", border_style="white")

# --- Actions ---

def install_comfyui():
    console.clear()
    console.print(Panel("[bold green]Installing ComfyUI...[/]", title="Installer"))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        
        # Step 1
        task1 = progress.add_task("[cyan]Cloning Repository...", total=100)
        if not os.path.exists(INSTALL_DIR):
            run_command(f"git clone {REPO_URL} {INSTALL_DIR}")
        else:
            run_command("git pull", cwd=INSTALL_DIR)
        progress.update(task1, completed=100)
        
        # Step 2
        task2 = progress.add_task("[cyan]Creating Venv...", total=100)
        venv_path = os.path.join(INSTALL_DIR, "venv")
        if not os.path.exists(venv_path):
            run_command(f"{sys.executable} -m venv venv", cwd=INSTALL_DIR)
        progress.update(task2, completed=100)
        
        # Step 3
        task3 = progress.add_task("[cyan]Installing Requirements (PyTorch)...", total=100)
        pip_cmd = os.path.join(venv_path, "bin", "pip")
        run_command(f"{pip_cmd} install --upgrade pip", cwd=INSTALL_DIR)
        run_command(f"{pip_cmd} install torch torchvision torchaudio", cwd=INSTALL_DIR)
        run_command(f"{pip_cmd} install -r requirements.txt", cwd=INSTALL_DIR)
        progress.update(task3, completed=100)
        
        # Step 4
        task4 = progress.add_task("[cyan]Installing Manager...", total=100)
        custom_nodes = os.path.join(INSTALL_DIR, "custom_nodes")
        os.makedirs(custom_nodes, exist_ok=True)
        manager_path = os.path.join(custom_nodes, "ComfyUI-Manager")
        if not os.path.exists(manager_path):
            run_command(f"git clone {MANAGER_URL}", cwd=custom_nodes)
        progress.update(task4, completed=100)

    console.print("[bold green]Installation Complete![/]")
    time.sleep(2)

def smoke_test():
    console.clear()
    console.print(Panel("[bold cyan]Running Smoke Test...[/]", title="Diagnostics"))
    
    if not is_installed():
        console.print("[bold red]ComfyUI is not installed. Cannot test.[/]")
        time.sleep(2)
        return

    venv_python = os.path.join(INSTALL_DIR, "venv", "bin", "python")
    # Start ComfyUI in background
    console.print("[dim]Starting server on port 8189 for testing...[/]")
    try:
        proc = subprocess.Popen(
            [venv_python, "main.py", "--port", "8189"], 
            cwd=INSTALL_DIR, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        
        # Poll for 15 seconds
        import urllib.request
        success = False
        for i in range(15):
            time.sleep(1)
            try:
                code = urllib.request.urlopen("http://127.0.0.1:8189").getcode()
                if code == 200:
                    success = True
                    break
            except:
                pass
        
        proc.terminate()
        
        if success:
            console.print(Panel("[bold green]PASS: Server started and responded to HTTP requests.[/]", border_style="green"))
        else:
            console.print(Panel("[bold red]FAIL: Server did not respond within 15 seconds.[/]", border_style="red"))
            
    except Exception as e:
        console.print(f"[bold red]Error running test: {e}[/]")
    
    console.input("\nPress Enter to return...")

def launch_app():
    if not is_installed():
        console.print("[red]Not installed![/]")
        time.sleep(1)
        return
        
    console.print("[green]Launching ComfyUI... (Press Ctrl+C in terminal to stop)[/]")
    venv_python = os.path.join(INSTALL_DIR, "venv", "bin", "python")
    os.system(f"cd {INSTALL_DIR} && {venv_python} main.py --auto-launch --force-fp16")

# --- Main Loop ---

def main():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )
    
    while True:
        # Update Dynamic Content
        layout["header"].update(generate_header())
        layout["left"].update(generate_stats())
        layout["right"].update(generate_health_panel())
        layout["footer"].update(generate_menu())
        
        # Render Frame
        console.clear()
        console.print(layout)
        
        # Input Handling
        choice = Prompt.ask("Select Option", choices=["1", "2", "3", "4", "5", "q", "Q"], default="q")
        
        if choice in ["q", "Q"]:
            console.print("Goodbye!")
            break
        elif choice == "1":
            install_comfyui()
        elif choice == "2":
            install_comfyui() # Logic is same (pulls changes)
        elif choice == "3":
            smoke_test()
        elif choice == "4":
            console.print("[dim]Use the 'Manager' inside ComfyUI to download models easily.[/]")
            time.sleep(2)
        elif choice == "5":
            launch_app()
            # Loop continues after launch closes
            
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\nExiting...")
        sys.exit(0)
