import customtkinter as ctk
import threading
import subprocess
import platform
from tkinter import messagebox
from src.services.system_service import SystemService
from src.services.dev_service import DevService

class DevToolsFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        ctk.CTkLabel(self, text="Developer Tools & CLIs", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
        
        # Node.js Check
        self.node_frame = ctk.CTkFrame(self)
        self.node_frame.pack(fill="x", pady=10)
        self.refresh_node_status()

        # CLIs
        self.cli_frame = ctk.CTkFrame(self)
        self.cli_frame.pack(fill="both", expand=True, pady=10)
        
        ctk.CTkLabel(self.cli_frame, text="AI Providers (CLI Tools)", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        self.cli_vars = {}
        self.refresh_cli_list()
        
        # Options
        opt = ctk.CTkFrame(self.cli_frame, fg_color="transparent")
        opt.pack(fill="x", padx=10, pady=10)
        self.scope_var = ctk.StringVar(value="user")
        ctk.CTkLabel(opt, text="Scope:").pack(side="left")
        ctk.CTkRadioButton(opt, text="User (Local)", variable=self.scope_var, value="user").pack(side="left", padx=10)
        ctk.CTkRadioButton(opt, text="System (Global -g)", variable=self.scope_var, value="system").pack(side="left", padx=10)
        
        ctk.CTkButton(self.cli_frame, text="Install Selected CLIs", fg_color="green", command=self.install_clis).pack(pady=20)

    def refresh_node_status(self):
        for w in self.node_frame.winfo_children(): w.destroy()
        
        ctk.CTkLabel(self.node_frame, text="Runtime Environment", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        status_row = ctk.CTkFrame(self.node_frame, fg_color="transparent")
        status_row.pack(fill="x", padx=10, pady=10)
        
        env = SystemService.verify_environment()
        
        for tool in ["node", "npm"]:
            icon = "✅" if env[tool] else "❌"
            ctk.CTkLabel(status_row, text=f"{icon} {tool}", width=80).pack(side="left", padx=10)
            
        if not env["node"]:
            ctk.CTkButton(self.node_frame, text="Install Node.js (LTS)", command=self.install_node).pack(side="right", padx=10, pady=5)

    def refresh_cli_list(self):
        # Clear existing
        for w in self.cli_frame.winfo_children(): 
            if isinstance(w, ctk.CTkFrame) and w != self.cli_frame: # Be careful not to destroy container parts if any
                pass 
                
        # Rebuild logic (Simplified: Just re-render the checkboxes area)
        # Note: In a real app we'd want a scrollable frame for CLIs if list grows.
        pass # The init builds it once. Phase 2: Make this dynamic.
        
        for tool_name in DevService.CLI_MAP.keys():
            if tool_name not in self.cli_vars: # Only add if not created
                row = ctk.CTkFrame(self.cli_frame, fg_color="transparent")
                row.pack(fill="x", pady=2, padx=20)
                
                is_inst = DevService.is_installed(tool_name)
                var = ctk.BooleanVar(value=is_inst)
                chk = ctk.CTkCheckBox(row, text=tool_name, variable=var)
                chk.pack(side="left")
                self.cli_vars[tool_name] = var
                
                if is_inst:
                    ctk.CTkLabel(row, text="✅ Installed", text_color="green", width=100).pack(side="left", padx=10)
                    chk.configure(state="disabled")
                else:
                    ctk.CTkLabel(row, text="Not Installed", text_color="gray", width=120).pack(side="left", padx=10)

    def install_node(self):
        # Phase 1: Keep simple shell open
        cmd = ["winget", "install", "-e", "--id", "OpenJS.NodeJS"] if platform.system() == "Windows" else ["echo", "Please install Node manually"]
        subprocess.Popen(cmd, shell=(platform.system()=="Windows"))
        messagebox.showinfo("Installer", "Launched Node.js installer.")

    def install_clis(self):
        scope = self.scope_var.get()
        targets = [t for t, v in self.cli_vars.items() if v.get() and not DevService.is_installed(t)]
        if not targets: 
            messagebox.showinfo("Info", "No new tools selected.")
            return

        def run():
            for t in targets:
                task_id = f"cli_{t.replace(' ', '_')}"
                self.app.add_activity(task_id, f"Installing {t}")
                self.app.update_activity(task_id, 0.3) # Partial progress
                
                cmd = DevService.get_install_cmd(t, scope)
                if cmd:
                    try:
                        subprocess.call(cmd, shell=(platform.system()=="Windows"))
                        self.app.update_activity(task_id, 1.0)
                    except Exception as e:
                        print(f"Install error: {e}")
                
                self.app.complete_activity(task_id)
            
            # Reset cache so UI can show 'Installed' status
            DevService.clear_cache()
            
        threading.Thread(target=run, daemon=True).start()
        messagebox.showinfo("Started", "CLI installations started in the Activity Center.")
