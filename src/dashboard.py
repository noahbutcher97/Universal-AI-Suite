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
import traceback
import requests

# --- CRASH CATCHER START ---
def main_wrapper():
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
        import customtkinter as ctk
        
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
                "Claude CLI": {"cmd": ["npm", "install", "@anthropic-ai/claude-code"], "type": "npm", "package": "@anthropic-ai/claude-code", "bin": "claude"},
                "Gemini CLI": {"cmd": ["npm", "install", "@google/gemini-cli"], "type": "npm", "package": "@google/gemini-cli", "bin": "gemini"},
                "Codex CLI": {"cmd": ["npm", "install", "@openai/codex"], "type": "npm", "package": "@openai/codex", "bin": "codex"},
                "Grok CLI": {"cmd": ["npm", "install", "@vibe-kit/grok-cli"], "type": "npm", "package": "@vibe-kit/grok-cli", "bin": "grok"},
                "DeepSeek CLI": {"cmd": ["pip", "install", "deepseek-cli"], "type": "pip", "package": "deepseek-cli", "bin": "deepseek-cli"}
            }

            @staticmethod
            def is_node_installed(): return shutil.which("node") is not None
            @staticmethod
            def is_npm_installed(): return shutil.which("npm") is not None
            @staticmethod
            def is_npx_installed(): return shutil.which("npx") is not None

            @staticmethod
            def check_cmd_output(cmd):
                try:
                    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=(platform.system()=="Windows"))
                    return True
                except: return False

            @staticmethod
            def is_installed(tool_name):
                tool = DevService.CLI_MAP.get(tool_name)
                if not tool: return False
                if "bin" in tool:
                    if shutil.which(tool["bin"]): return True
                    if tool_name == "DeepSeek CLI" and shutil.which("deepseek"): return True
                
                if tool["type"] == "npm":
                    if not DevService.is_npm_installed(): return False
                    return DevService.check_cmd_output(["npm", "list", "-g", tool["package"], "--depth=0"])
                
                if tool["type"] == "pip":
                    pkg = tool["package"]
                    if platform.system() == "Windows":
                        if DevService.check_cmd_output(["py", "-m", "pip", "show", pkg]): return True
                        if DevService.check_cmd_output(["python", "-m", "pip", "show", pkg]): return True
                    else:
                        if DevService.check_cmd_output(["python3", "-m", "pip", "show", pkg]): return True
                        if DevService.check_cmd_output(["python", "-m", "pip", "show", pkg]): return True
                    if DevService.check_cmd_output([sys.executable, "-m", "pip", "show", pkg]): return True
                return False

            @staticmethod
            def install_node_cmd():
                if platform.system() == "Darwin": return ["brew", "install", "node"]
                if platform.system() == "Windows": return ["winget", "install", "-e", "--id", "OpenJS.NodeJS"]
                return ["echo", "Manual install required on Linux"]

            @staticmethod
            def install_tool(tool_name, scope="user"):
                tool = DevService.CLI_MAP.get(tool_name)
                if not tool: return ["echo", f"Unknown tool: {tool_name}"]
                if tool["type"] == "npm" and not DevService.is_npm_installed():
                    return ["echo", f"Error: Cannot install {tool_name}. NPM is missing."]
                cmd = list(tool["cmd"])
                if tool["type"] == "npm":
                    if scope == "system": cmd.insert(2, "-g")
                elif tool["type"] == "pip":
                    if scope == "system" and platform.system() == "Windows": cmd = ["py", "-m"] + cmd
                    elif scope == "user": cmd.insert(2, "--user")
                return cmd

        class ComfyService:
            @staticmethod
            def detect_hardware():
                gpu_name = "CPU (Slow)"; vram_gb = 0
                try:
                    if shutil.which("nvidia-smi"):
                        output = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"]).decode()
                        name, mem = output.strip().split(',')
                        gpu_name = name; vram_gb = int(float(mem) / 1024)
                    elif platform.system() == "Darwin" and platform.machine() == "arm64":
                        gpu_name = "Apple Silicon (MPS)"; vram_gb = 16 
                except: pass
                return gpu_name, vram_gb

            @staticmethod
            def generate_recipe(answers, vram, install_root):
                manifest = []
                # 1. Base Installation
                manifest.append({"type": "clone", "url": "https://github.com/comfyanonymous/ComfyUI.git", "dest": install_root, "name": "ComfyUI Core"})
                manifest.append({"type": "clone", "url": "https://github.com/ltdrdata/ComfyUI-Manager.git", "dest": os.path.join(install_root, "custom_nodes", "ComfyUI-Manager"), "name": "ComfyUI Manager"})

                # 2. Model Selection
                model_tier = "sd15"
                if vram >= 16: model_tier = "flux"
                elif vram >= 8: model_tier = "sdxl"
                
                ckpt_dir = os.path.join(install_root, "models", "checkpoints")
                
                if answers["style"] == "Photorealistic":
                    if model_tier == "flux": 
                        manifest.append({"type": "download", "url": "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/flux1-schnell.safetensors", "dest": ckpt_dir, "name": "Flux1-Schnell"})
                    elif model_tier == "sdxl": 
                        manifest.append({"type": "download", "url": "https://civitai.com/api/download/models/240840", "dest": ckpt_dir, "name": "Juggernaut XL v9"})
                    else: 
                        manifest.append({"type": "download", "url": "https://civitai.com/api/download/models/130072", "dest": ckpt_dir, "name": "Realistic Vision 6"})
                        
                elif answers["style"] == "Anime":
                    if model_tier in ["sdxl", "flux"]: 
                        manifest.append({"type": "download", "url": "https://civitai.com/api/download/models/290640", "dest": ckpt_dir, "name": "Pony Diffusion V6 XL"})
                    else:
                        manifest.append({"type": "download", "url": "https://civitai.com/api/download/models/100675", "dest": ckpt_dir, "name": "Anything V5"})
                
                else: # General
                    if model_tier == "flux": 
                        manifest.append({"type": "download", "url": "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/flux1-schnell.safetensors", "dest": ckpt_dir, "name": "Flux1-Schnell"})
                    elif model_tier == "sdxl": 
                        manifest.append({"type": "download", "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors", "dest": ckpt_dir, "name": "SDXL Base 1.0"})
                    else: 
                        manifest.append({"type": "download", "url": "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors", "dest": ckpt_dir, "name": "SD 1.5 Pruned"})

                # 3. Features
                if answers["media"] in ["Video", "Mixed"]:
                    manifest.append({"type": "clone", "url": "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git", "dest": os.path.join(install_root, "custom_nodes", "ComfyUI-AnimateDiff-Evolved"), "name": "AnimateDiff Node"})
                    manifest.append({"type": "download", "url": "https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt", "dest": os.path.join(install_root, "custom_nodes", "ComfyUI-AnimateDiff-Evolved", "models"), "name": "AnimateDiff V2 Motion Model"})

                if answers["consistency"]:
                    manifest.append({"type": "clone", "url": "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git", "dest": os.path.join(install_root, "custom_nodes", "ComfyUI_IPAdapter_plus"), "name": "IPAdapter Plus"})
                    
                if answers["editing"]:
                    manifest.append({"type": "clone", "url": "https://github.com/Fannovel16/comfyui_controlnet_aux.git", "dest": os.path.join(install_root, "custom_nodes", "comfyui_controlnet_aux"), "name": "ControlNet Preprocessors"})
                    manifest.append({"type": "download", "url": "https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11p_sd15_canny.pth", "dest": os.path.join(install_root, "models", "controlnet"), "name": "ControlNet Canny (SD1.5)"})

                return manifest

        class App(ctk.CTk):
            def __init__(self):
                super().__init__()
                self.title("AI Universal Suite")
                self.geometry("1200x800")
                self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
                self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0); self.sidebar.grid(row=0, column=0, sticky="nsew")
                ctk.CTkLabel(self.sidebar, text="AI Universal\nSuite", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(30, 20))
                self.sidebar_btn("Dashboard", "overview"); self.sidebar_btn("Dev Tools (CLI)", "devtools"); self.sidebar_btn("ComfyUI Studio", "comfyui"); self.sidebar_btn("Settings & Keys", "settings")
                ctk.CTkButton(self.sidebar, text="Exit", fg_color="transparent", border_width=1, command=self.destroy).pack(side="bottom", pady=20, padx=20, fill="x")
                self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent"); self.content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
                self.frames = {}; self.init_frames(); self.show_frame("overview")

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

            def create_overview(self):
                frame = ctk.CTkFrame(self.content, fg_color="transparent")
                ctk.CTkLabel(frame, text="System Status", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
                gpu, vram = ComfyService.detect_hardware()
                info = ctk.CTkFrame(frame); info.pack(fill="x", pady=10)
                ctk.CTkLabel(info, text=f"OS: {platform.system()}").pack(side="left", padx=20, pady=15)
                ctk.CTkLabel(info, text=f"GPU: {gpu} ({vram}GB)").pack(side="left", padx=20, pady=15)
                return frame

            def create_devtools(self):
                frame = ctk.CTkFrame(self.content, fg_color="transparent")
                ctk.CTkLabel(frame, text="Developer Tools & CLIs", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
                node_frame = ctk.CTkFrame(frame); node_frame.pack(fill="x", pady=10)
                ctk.CTkLabel(node_frame, text="Runtime Environment", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
                status_row = ctk.CTkFrame(node_frame, fg_color="transparent"); status_row.pack(fill="x", padx=10, pady=10)
                node_inst = DevService.is_node_installed()
                ctk.CTkLabel(status_row, text="✅ node" if node_inst else "❌ node").pack(side="left", padx=10)
                ctk.CTkLabel(status_row, text="✅ npm" if DevService.is_npm_installed() else "❌ npm").pack(side="left", padx=10)
                ctk.CTkLabel(status_row, text="✅ npx" if DevService.is_npx_installed() else "❌ npx").pack(side="left", padx=10)
                if not node_inst: ctk.CTkButton(node_frame, text="Install Node.js (LTS)", command=self.install_node).pack(side="right", padx=10, pady=5)

                cli_frame = ctk.CTkFrame(frame); cli_frame.pack(fill="both", expand=True, pady=10)
                ctk.CTkLabel(cli_frame, text="AI Providers (CLI Tools)", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
                self.cli_vars = {}
                for tool_name, tool_data in DevService.CLI_MAP.items():
                    is_inst = DevService.is_installed(tool_name)
                    row = ctk.CTkFrame(cli_frame, fg_color="transparent"); row.pack(fill="x", pady=2, padx=20)
                    var = ctk.BooleanVar(value=is_inst)
                    chk = ctk.CTkCheckBox(row, text=tool_name, variable=var); chk.pack(side="left")
                    self.cli_vars[tool_name] = var
                    if is_inst:
                        ctk.CTkLabel(row, text="✅ Installed", text_color="green", width=100).pack(side="left", padx=10)
                        chk.configure(state="disabled")
                    else:
                        status_txt = "Not Installed"; status_col = "gray"
                        if tool_data["type"] == "npm" and not node_inst:
                            status_txt = "Requires Node.js"; status_col = "orange"; chk.configure(state="disabled")
                        ctk.CTkLabel(row, text=status_txt, text_color=status_col, width=120).pack(side="left", padx=10)
                opt = ctk.CTkFrame(cli_frame, fg_color="transparent"); opt.pack(fill="x", padx=10, pady=10)
                self.scope_var = ctk.StringVar(value="user")
                ctk.CTkLabel(opt, text="Scope:").pack(side="left")
                ctk.CTkRadioButton(opt, text="User (Local)", variable=self.scope_var, value="user").pack(side="left", padx=10)
                ctk.CTkRadioButton(opt, text="System (Global -g)", variable=self.scope_var, value="system").pack(side="left", padx=10)
                ctk.CTkButton(cli_frame, text="Install Selected CLIs", fg_color="green", command=self.install_clis).pack(pady=20)
                return frame

            def create_comfyui(self):
                frame = ctk.CTkFrame(self.content, fg_color="transparent")
                ctk.CTkLabel(frame, text="ComfyUI Studio", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
                path_frame = ctk.CTkFrame(frame); path_frame.pack(fill="x", pady=10)
                ctk.CTkLabel(path_frame, text="Install Location:").pack(side="left", padx=10)
                self.comfy_path_lbl = ctk.CTkLabel(path_frame, text=CONFIG["comfy_path"], text_color="cyan"); self.comfy_path_lbl.pack(side="left", padx=10)
                ctk.CTkButton(path_frame, text="Change", width=80, command=self.change_comfy_path).pack(side="right", padx=10)
                wiz = ctk.CTkFrame(frame); wiz.pack(fill="x", pady=20)
                ctk.CTkLabel(wiz, text="Installation Wizard", font=("Arial", 16, "bold")).pack(pady=10)
                ctk.CTkButton(wiz, text="✨ Build Installation Manifest", height=50, fg_color="#6A0dad", command=self.open_wizard).pack(pady=20, fill="x", padx=40)
                return frame

            def change_comfy_path(self):
                p = filedialog.askdirectory(initialdir=CONFIG["comfy_path"])
                if p: CONFIG["comfy_path"] = p; save_config(CONFIG); self.comfy_path_lbl.configure(text=p)

            def create_settings(self):
                frame = ctk.CTkFrame(self.content, fg_color="transparent")
                ctk.CTkLabel(frame, text="Settings & Keys", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
                self.key_entries = {}
                for provider in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROK_API_KEY", "DEEPSEEK_API_KEY"]:
                    row = ctk.CTkFrame(frame); row.pack(fill="x", pady=5)
                    ctk.CTkLabel(row, text=provider, width=150, anchor="w").pack(side="left", padx=10)
                    ent = ctk.CTkEntry(row, show="*"); ent.pack(side="left", fill="x", expand=True, padx=10)
                    val = CONFIG["api_keys"].get(provider, "")
                    if val: ent.insert(0, val)
                    self.key_entries[provider] = ent
                ctk.CTkButton(frame, text="Save Keys", command=self.save_keys).pack(pady=20)
                return frame

            def install_node(self):
                cmd = DevService.install_node_cmd()
                subprocess.Popen(cmd)
                messagebox.showinfo("Installer", "Launched Node.js installer.")

            def install_clis(self):
                scope = self.scope_var.get()
                targets = [t for t, v in self.cli_vars.items() if v.get() and not DevService.is_installed(t)]
                if not targets: messagebox.showinfo("Info", "No new tools selected."); return
                win = ctk.CTkToplevel(self); win.title("Installing..."); win.geometry("400x300")
                log = ctk.CTkTextbox(win); log.pack(fill="both", expand=True)
                def run():
                    for t in targets:
                        cmd = DevService.install_tool(t, scope)
                        log.insert("end", f"Installing {t}...\n"); log.see("end")
                        try: subprocess.call(cmd, shell=(platform.system()=="Windows")); log.insert("end", "Done.\n")
                        except Exception as e: log.insert("end", f"Error: {e}\n")
                    log.insert("end", "All tasks finished.")
                threading.Thread(target=run, daemon=True).start()

            def open_wizard(self):
                win = ctk.CTkToplevel(self); win.title("Setup Wizard"); win.geometry("600x700")
                gpu, vram = ComfyService.detect_hardware()
                ctk.CTkLabel(win, text=f"Detected: {gpu} ({vram} GB)", text_color="yellow").pack(pady=10)
                ctk.CTkLabel(win, text="Art Style").pack(anchor="w", padx=20)
                style_var = ctk.StringVar(value="General"); ctk.CTkSegmentedButton(win, values=["Photorealistic", "Anime", "General"], variable=style_var).pack(fill="x", padx=20)
                ctk.CTkLabel(win, text="Media Type").pack(anchor="w", padx=20, pady=(10,0))
                media_var = ctk.StringVar(value="Image"); ctk.CTkSegmentedButton(win, values=["Image", "Video", "Mixed"], variable=media_var).pack(fill="x", padx=20)
                consist_var = ctk.BooleanVar(); ctk.CTkCheckBox(win, text="Consistency (IPAdapter)", variable=consist_var).pack(anchor="w", padx=20, pady=10)
                edit_var = ctk.BooleanVar(); ctk.CTkCheckBox(win, text="Editing (ControlNet)", variable=edit_var).pack(anchor="w", padx=20, pady=5)
                def review():
                    ans = {"style": style_var.get(), "media": media_var.get(), "consistency": consist_var.get(), "editing": edit_var.get()}
                    manifest = ComfyService.generate_recipe(ans, vram, CONFIG["comfy_path"])
                    self.show_manifest_review(win, manifest)
                ctk.CTkButton(win, text="Next: Review Manifest", command=review).pack(side="bottom", fill="x", padx=20, pady=20)

            def show_manifest_review(self, parent, manifest):
                for w in parent.winfo_children(): w.destroy()
                parent.title("Review Manifest")
                ctk.CTkLabel(parent, text="Installation Manifest", font=("Arial", 18, "bold")).pack(pady=10)
                tree_frame = ctk.CTkFrame(parent); tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
                tree = ttk.Treeview(tree_frame, columns=("dest"), show="tree headings")
                tree.heading("#0", text="Component / Model"); tree.heading("dest", text="Destination Folder")
                tree.column("#0", width=250); tree.column("dest", width=300); tree.pack(fill="both", expand=True)
                for item in manifest:
                    short_dest = item['dest'].replace(CONFIG['comfy_path'], "...")
                    tree.insert("", "end", text=item['name'], values=(short_dest,))
                def execute():
                    parent.destroy(); self.run_install_process(manifest)
                ctk.CTkButton(parent, text="Confirm & Install", fg_color="green", height=50, command=execute).pack(fill="x", padx=20, pady=20)

            def run_install_process(self, manifest):
                win = ctk.CTkToplevel(self); win.title("Installing..."); win.geometry("600x400")
                log = ctk.CTkTextbox(win); log.pack(fill="both", expand=True)
                def process():
                    log.insert("end", "Checking Python Environment...\n")
                    venv_py = ComfyService.get_venv_python()
                    if not os.path.exists(venv_py):
                        log.insert("end", "Creating venv...\n")
                        subprocess.call([sys.executable, "-m", "venv", "venv"], cwd=CONFIG["comfy_path"])
                    for item in manifest:
                        log.insert("end", f"Processing: {item['name']}...\n"); log.see("end")
                        if not os.path.exists(item['dest']): os.makedirs(item['dest'], exist_ok=True)
                        if item['type'] == "clone":
                            if not os.path.exists(os.path.join(item['dest'], ".git")): subprocess.call(["git", "clone", item['url'], item['dest']], stdout=subprocess.DEVNULL)
                            else: log.insert("end", "  Already exists, skipping.\n")
                        elif item['type'] == "download":
                            fname = item['url'].split('/')[-1]; dest_file = os.path.join(item['dest'], fname)
                            if not os.path.exists(dest_file):
                                log.insert("end", f"  Downloading {fname}...\n")
                                try:
                                    response = requests.get(item['url'], stream=True)
                                    with open(dest_file, 'wb') as f: 
                                        for data in response.iter_content(1024): f.write(data)
                                    log.insert("end", "  Download complete.\n")
                                except: log.insert("end", "  Download FAILED.\n")
                            else: log.insert("end", "  File exists.\n")
                    log.insert("end", "\n✅ All operations complete.\n")
                try: import requests
                except: subprocess.call([sys.executable, "-m", "pip", "install", "requests"])
                threading.Thread(target=process, daemon=True).start()

            def save_keys(self):
                for k, ent in self.key_entries.items(): CONFIG["api_keys"][k] = ent.get()
                save_config(CONFIG); messagebox.showinfo("Saved", "API Keys saved securely.")

        app = App(); app.mainloop()
    except Exception as e: 
        print("\n\n" + "="*60); print("CRITICAL ERROR"); print("="*60); traceback.print_exc(); input("Press Enter...")

if __name__ == "__main__":
    main_wrapper()
