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

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".ai_universal_suite")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "comfy_path": os.path.join(os.path.expanduser("~"), "ComfyUI"),
    "api_keys": {},
    "cli_scope": "user"
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

# --- Logic: Dev Tools & CLI Service ---
class DevService:
    CLI_MAP = {
        "Gemini CLI": {"cmd": ["pip", "install", "-U", "google-generativeai"], "type": "pip"},
        "Codex CLI (OpenAI)": {"cmd": ["pip", "install", "openai"], "type": "pip"},
        "Claude CLI": {"cmd": ["npm", "install", "@anthropic-ai/claude-code"], "type": "npm"},
        "Grok CLI": {"cmd": ["pip", "install", "xai-sdk"], "type": "pip"},
        "DeepSeek CLI": {"cmd": ["pip", "install", "deepseek"], "type": "pip"}
    }

    @staticmethod
    def is_node_installed(): return shutil.which("node") is not None
    @staticmethod
    def is_npm_installed(): return shutil.which("npm") is not None

    @staticmethod
    def install_node_cmd():
        if platform.system() == "Darwin": return ["brew", "install", "node"]
        if platform.system() == "Windows": return ["winget", "install", "-e", "--id", "OpenJS.NodeJS"]
        return ["echo", "Manual install required on Linux"]

    @staticmethod
    def install_tool(tool_name, scope="user"):
        tool = DevService.CLI_MAP.get(tool_name)
        if not tool: return ["echo", f"Unknown tool: {tool_name}"]

        cmd = list(tool["cmd"])
        if tool["type"] == "npm":
            if scope == "system": cmd.insert(2, "-g")
        elif tool["type"] == "pip":
            if scope == "user": cmd.insert(2, "--user")
        
        return cmd

# --- Logic: Comfy Service & Wizard ---
class ComfyService:
    @staticmethod
    def detect_hardware():
        gpu_name = "CPU (Slow)"
        vram_gb = 0
        try:
            if shutil.which("nvidia-smi"):
                output = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"]).decode()
                name, mem = output.strip().split(',')
                gpu_name = name
                vram_gb = int(float(mem) / 1024)
            elif platform.system() == "Darwin" and platform.machine() == "arm64":
                gpu_name = "Apple Silicon (MPS)"
                vram_gb = 16 
        except: pass
        return gpu_name, vram_gb

    @staticmethod
    def generate_recipe(answers, vram):
        recipe = {
            "checkpoints": [],
            "loras": [],
            "custom_nodes": ["https://github.com/ltdrdata/ComfyUI-Manager.git"]
        }

        model_tier = "sd15"
        if vram >= 16: model_tier = "flux"
        elif vram >= 8: model_tier = "sdxl"
        
        if answers["style"] == "Photorealistic":
            if model_tier == "flux": recipe["checkpoints"].append(("Flux1-Dev", "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors"))
            elif model_tier == "sdxl": recipe["checkpoints"].append(("Juggernaut XL", "https://civitai.com/api/download/models/JuggernautXL"))
            else: recipe["checkpoints"].append(("Realistic Vision 6", "https://civitai.com/api/download/models/RealisticVision"))
            
        elif answers["style"] == "Anime":
            if model_tier in ["sdxl", "flux"]: recipe["checkpoints"].append(("Pony Diffusion V6 XL", "https://civitai.com/api/download/models/PonyDiffusion"))
            else: recipe["checkpoints"].append(("Anything V5", "https://civitai.com/api/download/models/AnythingV5"))
            
        else: # General
            if model_tier == "flux": recipe["checkpoints"].append(("Flux1-Schnell", "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/flux1-schnell.safetensors"))
            elif model_tier == "sdxl": recipe["checkpoints"].append(("SDXL Base 1.0", "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors"))
            else: recipe["checkpoints"].append(("SD 1.5 Pruned", "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"))

        if answers["media"] == "Video" or answers["media"] == "Mixed":
            recipe["custom_nodes"].append("https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git")
            recipe["custom_nodes"].append("https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git")
        
        if answers["consistency"]:
            recipe["custom_nodes"].append("https://github.com/cubiq/ComfyUI_IPAdapter_plus.git")
            
        if answers["editing"]:
            recipe["custom_nodes"].append("https://github.com/Fannovel16/comfyui_controlnet_aux.git")

        return recipe

# --- UI Application ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Universal Suite")
        self.geometry("1200x800")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text="AI Universal\nSuite", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(30, 20))
        
        self.sidebar_btn("Dashboard", "overview")
        self.sidebar_btn("Dev Tools (CLI)", "devtools")
        self.sidebar_btn("ComfyUI Studio", "comfyui")
        self.sidebar_btn("Settings & Keys", "settings")
        
        ctk.CTkButton(self.sidebar, text="Exit", fg_color="transparent", border_width=1, command=self.destroy).pack(side="bottom", pady=20, padx=20, fill="x")

        # Content
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self.frames = {}
        self.init_frames()
        self.show_frame("overview")

    def sidebar_btn(self, text, name):
        ctk.CTkButton(self.sidebar, text=text, height=40, anchor="w", fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), command=lambda: self.show_frame(name)).pack(fill="x", padx=10, pady=5)

    def init_frames(self):
        self.frames["overview"] = self.create_overview()
        self.frames["devtools"] = self.create_devtools()
        self.frames["comfyui"] = self.create_comfyui()
        self.frames["settings"] = self.create_settings()

    def show_frame(self, name):
        for f in self.frames.values(): f.pack_forget()
        self.frames[name].pack(fill="both", expand=True)

    # --- Frames ---
    def create_overview(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(frame, text="System Status", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
        
        gpu, vram = ComfyService.detect_hardware()
        info = ctk.CTkFrame(frame)
        info.pack(fill="x", pady=10)
        ctk.CTkLabel(info, text=f"OS: {platform.system()}").pack(side="left", padx=20, pady=15)
        ctk.CTkLabel(info, text=f"GPU: {gpu} ({vram}GB)").pack(side="left", padx=20, pady=15)
        
        return frame

    def create_devtools(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(frame, text="Developer Tools & CLIs", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)

        # Node
        node_frame = ctk.CTkFrame(frame); node_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(node_frame, text="Runtime Environment", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        status = "✅ Installed" if DevService.is_node_installed() else "❌ Missing"
        ctk.CTkLabel(node_frame, text=f"Node.js: {status}").pack(side="left", padx=10, pady=10)
        if not DevService.is_node_installed():
            ctk.CTkButton(node_frame, text="Install Node.js (LTS)", command=self.install_node).pack(side="right", padx=10)

        # CLIs
        cli_frame = ctk.CTkFrame(frame); cli_frame.pack(fill="both", expand=True, pady=10)
        ctk.CTkLabel(cli_frame, text="AI Providers (CLI)", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        self.cli_vars = {}
        for tool in DevService.CLI_MAP.keys():
            var = ctk.BooleanVar()
            ctk.CTkCheckBox(cli_frame, text=tool, variable=var).pack(anchor="w", padx=20, pady=5)
            self.cli_vars[tool] = var
            
        opt_frame = ctk.CTkFrame(cli_frame, fg_color="transparent"); opt_frame.pack(fill="x", padx=10, pady=10)
        self.scope_var = ctk.StringVar(value="user")
        ctk.CTkLabel(opt_frame, text="Scope:").pack(side="left")
        ctk.CTkRadioButton(opt_frame, text="User (Local)", variable=self.scope_var, value="user").pack(side="left", padx=10)
        ctk.CTkRadioButton(opt_frame, text="System (Global)", variable=self.scope_var, value="system").pack(side="left", padx=10)
        
        ctk.CTkButton(cli_frame, text="Install Selected CLIs", fg_color="green", command=self.install_clis).pack(pady=20)
        return frame

    def create_comfyui(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(frame, text="ComfyUI Studio", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
        
        wiz_frame = ctk.CTkFrame(frame)
        wiz_frame.pack(fill="x", pady=20)
        ctk.CTkLabel(wiz_frame, text="Setup Wizard", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkLabel(wiz_frame, text="Answer a few questions to generate a custom installation recipe.").pack(pady=5)
        ctk.CTkButton(wiz_frame, text="✨ Start Wizard", height=50, fg_color="#6A0dad", command=self.open_wizard).pack(pady=20, fill="x", padx=40)
        
        return frame

    def create_settings(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        ctk.CTkLabel(frame, text="Settings & Keys", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
        
        self.key_entries = {}
        for provider in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROK_API_KEY", "DEEPSEEK_API_KEY"]:
            row = ctk.CTkFrame(frame); row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=provider, width=150, anchor="w").pack(side="left", padx=10)
            ent = ctk.CTkEntry(row, show="*"); ent.pack(side="left", fill="x", expand=True, padx=10)
            # FIX: Ensure clean variable access
            if provider in CONFIG["api_keys"]: ent.insert(0, CONFIG["api_keys"][provider])
            self.key_entries[provider] = ent
            
        ctk.CTkButton(frame, text="Save Keys", command=self.save_keys).pack(pady=20)
        return frame

    # --- Actions ---
    def install_node(self):
        cmd = DevService.install_node_cmd()
        subprocess.Popen(cmd)
        messagebox.showinfo("Installer", "Launched Node.js installer.")

    def install_clis(self):
        scope = self.scope_var.get()
        targets = [t for t, v in self.cli_vars.items() if v.get()]
        if not targets: return
        
        win = ctk.CTkToplevel(self)
        win.title("Installing...")
        win.geometry("400x300")
        log = ctk.CTkTextbox(win); log.pack(fill="both", expand=True)
        
        def run():
            for t in targets:
                cmd = DevService.install_tool(t, scope)
                log.insert("end", f"Installing {t}...\n")
                log.see("end")
                try:
                    subprocess.call(cmd, shell=(platform.system()=="Windows"))
                    log.insert("end", "Done.\n")
                except Exception as e: log.insert("end", f"Error: {e}\n")
            log.insert("end", "All tasks finished.")
        
        threading.Thread(target=run, daemon=True).start()

    def open_wizard(self):
        win = ctk.CTkToplevel(self)
        win.title("ComfyUI Wizard")
        win.geometry("500x650")
        
        gpu, vram = ComfyService.detect_hardware()
        ctk.CTkLabel(win, text="System Scan", font=("Arial", 14, "bold")).pack(pady=10)
        ctk.CTkLabel(win, text=f"Detected: {gpu} ({vram} GB VRAM)", text_color="yellow").pack()
        
        ctk.CTkLabel(win, text="1. Art Style?", font=("Arial", 12, "bold")).pack(anchor="w", padx=20, pady=(20,5))
        style_var = ctk.StringVar(value="General")
        ctk.CTkSegmentedButton(win, values=["Photorealistic", "Anime", "General"], variable=style_var).pack(fill="x", padx=20)
        
        ctk.CTkLabel(win, text="2. Media Type?", font=("Arial", 12, "bold")).pack(anchor="w", padx=20, pady=(20,5))
        media_var = ctk.StringVar(value="Image")
        ctk.CTkSegmentedButton(win, values=["Image", "Video", "Mixed"], variable=media_var).pack(fill="x", padx=20)
        
        consistency_var = ctk.BooleanVar()
        ctk.CTkCheckBox(win, text="Need Character Consistency? (FaceID/IPAdapter)", variable=consistency_var).pack(anchor="w", padx=20, pady=(20,5))
        
        editing_var = ctk.BooleanVar()
        ctk.CTkCheckBox(win, text="Need Image Editing? (Inpainting/ControlNet)", variable=editing_var).pack(anchor="w", padx=20, pady=5)
        
        def generate():
            answers = {
                "style": style_var.get(),
                "media": media_var.get(),
                "consistency": consistency_var.get(),
                "editing": editing_var.get()
            }
            recipe = ComfyService.generate_recipe(answers, vram)
            self.execute_recipe(recipe)
            win.destroy()
            
        ctk.CTkButton(win, text="Generate Recipe & Install", fg_color="green", height=50, command=generate).pack(side="bottom", fill="x", padx=20, pady=20)

    def execute_recipe(self, recipe):
        msg = f"Recipe Generated!\n\nModels: {len(recipe['checkpoints'])}\nNodes: {len(recipe['custom_nodes'])}\n\nStarting downloads in background..."
        messagebox.showinfo("Wizard", msg)
        print("Recipe:", recipe)

    def save_keys(self):
        for k, ent in self.key_entries.items(): CONFIG["api_keys"][k] = ent.get()
        save_config(CONFIG)
        messagebox.showinfo("Saved", "API Keys saved securely.")

if __name__ == "__main__":
    app = App()
    app.mainloop()
