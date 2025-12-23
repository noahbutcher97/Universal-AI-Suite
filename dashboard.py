import os
import sys
import shutil
import subprocess
import platform
import psutil
import json
import threading
import time
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk

# --- Config & Constants ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".comfy_dashboard")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
REPO_URL = "https://github.com/comfyanonymous/ComfyUI.git"
MANAGER_URL = "https://github.com/ltdrdata/ComfyUI-Manager.git"

DEFAULT_CONFIG = {
    "install_path": os.path.join(os.path.expanduser("~"), "ComfyUI"),
    "auto_launch": False
}

def load_config():
    if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR)
    if not os.path.exists(CONFIG_FILE): save_config(DEFAULT_CONFIG); return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    except: return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, 'w') as f: json.dump(config, f, indent=4)

CONFIG = load_config()
INSTALL_DIR = CONFIG["install_path"]

# --- Backend Service (Internal API) ---
class ModelService:
    MODEL_TYPES = {
        "Checkpoints": "checkpoints",
        "LoRAs": "loras",
        "VAE": "vae",
        "ControlNet": "controlnet",
        "Embeddings": "embeddings",
        "Upscale": "upscale_models"
    }

    @staticmethod
    def get_root_path(model_type):
        return os.path.join(INSTALL_DIR, "models", ModelService.MODEL_TYPES.get(model_type, "checkpoints"))

    @staticmethod
    def list_files(model_type, subfolder=""):
        root = ModelService.get_root_path(model_type)
        target_dir = os.path.join(root, subfolder)
        if not os.path.exists(target_dir): return []

        items = []
        for name in os.listdir(target_dir):
            path = os.path.join(target_dir, name)
            stats = os.stat(path)
            items.append({
                "name": name,
                "type": "folder" if os.path.isdir(path) else "file",
                "size": stats.st_size,
                "date": datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M'),
                "path": path
            })
        return items

    @staticmethod
    def add_file(model_type, source_path, dest_subfolder=""):
        dest_dir = os.path.join(ModelService.get_root_path(model_type), dest_subfolder)
        if not os.path.exists(dest_dir): os.makedirs(dest_dir)
        filename = os.path.basename(source_path)
        dest_path = os.path.join(dest_dir, filename)
        try:
            shutil.copy2(source_path, dest_path)
            return {"status": "success", "path": dest_path}
        except Exception as e: return {"status": "error", "message": str(e)}

    @staticmethod
    def delete_item(path):
        try:
            if os.path.isdir(path): shutil.rmtree(path)
            else: os.remove(path)
            return {"status": "success"}
        except Exception as e: return {"status": "error", "message": str(e)}

    @staticmethod
    def create_folder(model_type, folder_name, subfolder=""):
        target_dir = os.path.join(ModelService.get_root_path(model_type), subfolder, folder_name)
        try:
            os.makedirs(target_dir, exist_ok=False)
            return {"status": "success", "path": target_dir}
        except Exception as e: return {"status": "error", "message": str(e)}

# --- Helper Logic ---
class Logic:
    @staticmethod
    def get_venv_python():
        if platform.system() == "Windows": return os.path.join(INSTALL_DIR, "venv", "Scripts", "python.exe")
        return os.path.join(INSTALL_DIR, "venv", "bin", "python")

    @staticmethod
    def get_venv_pip():
        if platform.system() == "Windows": return os.path.join(INSTALL_DIR, "venv", "Scripts", "pip.exe")
        return os.path.join(INSTALL_DIR, "venv", "bin", "pip")

    @staticmethod
    def is_installed(): return os.path.exists(os.path.join(INSTALL_DIR, "main.py"))

    @staticmethod
    def open_folder(path):
        if not os.path.exists(path): return
        if platform.system() == "Windows": os.startfile(path)
        elif platform.system() == "Darwin": subprocess.run(["open", path])
        else: subprocess.run(["xdg-open", path])

# --- Main App ---
class DashboardApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ComfyUI Universal Dashboard")
        self.geometry("1100x750")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(self.sidebar, text="ComfyUI\nDashboard", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))
        ctk.CTkButton(self.sidebar, text="Overview", command=lambda: self.show_frame("overview")).grid(row=1, column=0, padx=20, pady=10)
        ctk.CTkButton(self.sidebar, text="Install / Update", command=lambda: self.show_frame("install")).grid(row=2, column=0, padx=20, pady=10)
        ctk.CTkButton(self.sidebar, text="Model Manager", command=lambda: self.show_frame("models")).grid(row=3, column=0, padx=20, pady=10)
        ctk.CTkButton(self.sidebar, text="Settings", command=lambda: self.show_frame("settings")).grid(row=4, column=0, padx=20, pady=10)
        ctk.CTkButton(self.sidebar, text="Exit", fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"), command=self.destroy).grid(row=6, column=0, padx=20, pady=20)

        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self.frames = {}
        self.setup_overview_frame()
        self.setup_install_frame()
        self.setup_models_frame()
        self.setup_settings_frame()

        self.show_frame("overview")
        self.update_metrics()

    def show_frame(self, name):
        for frame in self.frames.values(): frame.pack_forget()
        self.frames[name].pack(fill="both", expand=True)

    def setup_overview_frame(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["overview"] = frame
        self.status_label = ctk.CTkLabel(frame, text="Checking status...", font=ctk.CTkFont(size=16))
        self.status_label.pack(pady=10, anchor="w")
        
        metrics = ctk.CTkFrame(frame)
        metrics.pack(fill="x", pady=10)
        ctk.CTkLabel(metrics, text="System Metrics").pack(pady=5)
        self.cpu_bar = ctk.CTkProgressBar(metrics); self.cpu_bar.pack(fill="x", padx=10, pady=5)
        self.cpu_label = ctk.CTkLabel(metrics, text="CPU: 0%"); self.cpu_label.pack(anchor="e", padx=10)
        self.ram_bar = ctk.CTkProgressBar(metrics); self.ram_bar.set(0); self.ram_bar.pack(fill="x", padx=10, pady=5)
        self.ram_label = ctk.CTkLabel(metrics, text="RAM: 0%"); self.ram_label.pack(anchor="e", padx=10)
        
        self.btn_launch = ctk.CTkButton(frame, text="🚀 Launch ComfyUI", height=50, font=ctk.CTkFont(size=18), command=self.launch_comfyui)
        self.btn_launch.pack(pady=30, fill="x")
        ctk.CTkButton(frame, text="🧪 Run Smoke Test", fg_color="gray", command=self.run_smoke_test).pack(pady=5, fill="x")

    def update_metrics(self):
        try:
            cpu = psutil.cpu_percent() / 100; ram = psutil.virtual_memory().percent / 100
            self.cpu_bar.set(cpu); self.cpu_label.configure(text=f"CPU: {int(cpu*100)}%")
            self.ram_bar.set(ram); self.ram_label.configure(text=f"RAM: {int(ram*100)}%")
            if Logic.is_installed():
                self.status_label.configure(text=f"✅ ComfyUI Installed at: {INSTALL_DIR}", text_color="green")
                self.btn_launch.configure(state="normal")
            else:
                self.status_label.configure(text=f"❌ ComfyUI Not Found at: {INSTALL_DIR}", text_color="red")
                self.btn_launch.configure(state="disabled")
        except: pass
        self.after(2000, self.update_metrics)

    def setup_install_frame(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["install"] = frame
        controls = ctk.CTkFrame(frame); controls.pack(fill="x", pady=10)
        ctk.CTkButton(controls, text="Install (Clean)", command=self.do_install).pack(side="left", padx=5, expand=True, fill="x")
        ctk.CTkButton(controls, text="Update (Git Pull)", command=self.do_update).pack(side="left", padx=5, expand=True, fill="x")
        ctk.CTkButton(controls, text="Install Node.js", fg_color="orange", command=self.do_install_node).pack(side="left", padx=5, expand=True, fill="x")
        self.console_log = ctk.CTkTextbox(frame, font=("Consolas", 12)); self.console_log.pack(fill="both", expand=True, pady=10)
        self.log("Ready.")

    def log(self, msg):
        self.console_log.insert("end", str(msg) + "\n"); self.console_log.see("end")

    def setup_models_frame(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["models"] = frame
        
        self.cat_var = ctk.StringVar(value="Checkpoints")
        # Define on_cat_change BEFORE using it in the button command
        # Note: In python class methods, order doesn't matter for calling, but self.method must exist.
        
        self.cat_buttons = ctk.CTkSegmentedButton(frame, values=list(ModelService.MODEL_TYPES.keys()), command=self.on_cat_change, variable=self.cat_var)
        self.cat_buttons.pack(fill="x", pady=(0, 10))

        toolbar = ctk.CTkFrame(frame); toolbar.pack(fill="x", pady=5)
        ctk.CTkButton(toolbar, text="Import Files", command=self.import_model_files, fg_color="green").pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Create Folder", command=self.create_model_folder).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Refresh", command=self.refresh_file_list).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Delete Selected", command=self.delete_selected_item, fg_color="red").pack(side="right", padx=5)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0)
        style.map('Treeview', background=[('selected', '#1f538d')])
        
        self.tree = ttk.Treeview(frame, columns=("size", "date"), show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Name", anchor="w"); self.tree.heading("size", text="Size", anchor="e"); self.tree.heading("date", text="Date", anchor="w")
        self.tree.column("#0", width=300); self.tree.column("size", width=100, anchor="e"); self.tree.column("date", width=150)
        self.tree.pack(fill="both", expand=True, pady=5)
        
        self.current_subfolder = ""
        # Defer initial load to avoid startup lag/race condition
        self.after(100, self.refresh_file_list)

    def on_cat_change(self, value):
        self.current_subfolder = ""
        self.refresh_file_list()

    def refresh_file_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        category = self.cat_var.get()
        items = ModelService.list_files(category, self.current_subfolder)
        for item in items:
            size_str = f"{item['size'] / (1024*1024):.1f} MB" if item['type'] == "file" else ""
            icon = "📁 " if item['type'] == "folder" else "📄 "
            iid = self.tree.insert("", "end", text=f"{icon}{item['name']}", values=(size_str, item['date']))
            self.tree.item(iid, tags=(item['path'], item['type']))

    def import_model_files(self):
        category = self.cat_var.get()
        files = filedialog.askopenfilenames(title=f"Select {category} to Import")
        if files:
            count = 0
            for f in files:
                res = ModelService.add_file(category, f, self.current_subfolder)
                if res["status"] == "success": count += 1
            messagebox.showinfo("Import", f"Imported {count} files.")
            self.refresh_file_list()

    def create_model_folder(self):
        name = ctk.CTkInputDialog(text="Folder Name:", title="New Folder").get_input()
        if name:
            res = ModelService.create_folder(self.cat_var.get(), name, self.current_subfolder)
            if res["status"] == "success": self.refresh_file_list()
            else: messagebox.showerror("Error", res["message"])

    def delete_selected_item(self):
        selected = self.tree.selection()
        if not selected: return
        item = self.tree.item(selected[0])
        if messagebox.askyesno("Delete", f"Delete '{item['text']}'?"):
            ModelService.delete_item(item['tags'][0])
            self.refresh_file_list()

    def setup_settings_frame(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["settings"] = frame
        ctk.CTkLabel(frame, text="Installation Path").pack(anchor="w")
        self.path_entry = ctk.CTkEntry(frame); self.path_entry.insert(0, INSTALL_DIR); self.path_entry.pack(fill="x", pady=5)
        ctk.CTkButton(frame, text="Browse...", command=self.browse_path).pack(anchor="e", pady=5)
        ctk.CTkButton(frame, text="Save Config", command=self.save_settings, fg_color="green").pack(pady=20)

    def browse_path(self):
        path = filedialog.askdirectory(initialdir=INSTALL_DIR)
        if path: self.path_entry.delete(0, "end"); self.path_entry.insert(0, path)

    def save_settings(self):
        global INSTALL_DIR
        new_path = self.path_entry.get()
        CONFIG["install_path"] = new_path
        save_config(CONFIG)
        INSTALL_DIR = new_path
        messagebox.showinfo("Saved", "Settings saved.")

    def launch_comfyui(self):
        if not Logic.is_installed(): return
        args = ["--auto-launch"]
        if platform.system() == "Darwin": args.append("--force-fp16")
        subprocess.Popen([Logic.get_venv_python(), "main.py"] + args, cwd=INSTALL_DIR)
        messagebox.showinfo("Launch", "ComfyUI Launched!")

    def run_smoke_test(self):
        self.log("Starting Smoke Test...")
        def _test():
            try:
                proc = subprocess.Popen([Logic.get_venv_python(), "main.py", "--port", "8199", "--cpu"], cwd=INSTALL_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                import urllib.request; success = False
                for _ in range(15):
                    time.sleep(1)
                    try:
                        if urllib.request.urlopen("http://127.0.0.1:8199").getcode() == 200: success = True; break
                    except: pass
                proc.terminate()
                self.log("Smoke Test Passed: ✅" if success else "Smoke Test Failed: ❌")
            except Exception as e: self.log(f"Test Error: {e}")
        self.run_thread("test", _test)

    def run_thread(self, name, target): threading.Thread(target=target, daemon=True).start()

    def do_install(self):
        def _install():
            self.log("Cloning...")
            if not os.path.exists(INSTALL_DIR): subprocess.call(["git", "clone", REPO_URL, INSTALL_DIR])
            self.log("Venv...")
            subprocess.call([sys.executable, "-m", "venv", "venv"], cwd=INSTALL_DIR)
            self.log("Deps...")
            pip = Logic.get_venv_pip()
            subprocess.call([pip, "install", "--upgrade", "pip"], cwd=INSTALL_DIR)
            subprocess.call([pip, "install", "torch", "torchvision", "torchaudio"], cwd=INSTALL_DIR)
            subprocess.call([pip, "install", "-r", "requirements.txt"], cwd=INSTALL_DIR)
            self.log("Done!")
        self.run_thread("install", _install)

    def do_update(self):
        def _update():
            self.log("Git Pulling...")
            subprocess.call(["git", "pull"], cwd=INSTALL_DIR)
            self.log("Updating Deps...")
            subprocess.call([Logic.get_venv_pip(), "install", "-r", "requirements.txt"], cwd=INSTALL_DIR)
            self.log("Updated.")
        self.run_thread("update", _update)

    def do_install_node(self):
        def _node():
            self.log("Installing Node.js...")
            if platform.system() == "Darwin": subprocess.call(["brew", "install", "node"])
            elif platform.system() == "Windows": subprocess.call(["winget", "install", "-e", "--id", "OpenJS.NodeJS"])
            self.log("Finished.")
        self.run_thread("node", _node)

if __name__ == "__main__":
    app = DashboardApp()
    app.mainloop()
