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
        self.cli_widgets_frame = ctk.CTkFrame(self.cli_frame, fg_color="transparent") # Frame to hold checkboxes
        self.cli_widgets_frame.pack(fill="x", pady=5, padx=20)
        
        # Options
        opt = ctk.CTkFrame(self.cli_frame, fg_color="transparent")
        opt.pack(fill="x", padx=10, pady=10)
        self.scope_var = ctk.StringVar(value="user")
        ctk.CTkLabel(opt, text="Scope:").pack(side="left")
        ctk.CTkRadioButton(opt, text="User (Local)", variable=self.scope_var, value="user").pack(side="left", padx=10)
        ctk.CTkRadioButton(opt, text="System (Global -g)", variable=self.scope_var, value="system").pack(side="left", padx=10)
        
        # #TODO: Add a refresh button for the CLI list.
        # Currently, the list refreshes on startup and after installation.
        # A manual refresh button would be useful if the user installs or
        # uninstalls a tool outside of this application.
        #
        # Suggested implementation:
        # 1. Add a `CTkButton` next to the "Install Selected CLIs" button.
        # 2. Bind its command to `self.refresh_cli_list`.

        ctk.CTkButton(self.cli_frame, text="Install Selected CLIs", fg_color="green", command=self.install_clis).pack(pady=20)

        self.refresh_cli_list() # Initial population

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

    def _update_cli_list_ui(self, statuses):
        # Clear existing
        for w in self.cli_widgets_frame.winfo_children():
            w.destroy()
        
        # #TODO: Improve the layout for the CLI list to be scalable.
        # The current implementation uses a simple `pack` layout, which will
        # become unusable if the number of CLI tools grows.
        #
        # Suggested implementation:
        # 1. Use a `CTkScrollableFrame` to contain the list of tools.
        # 2. Consider using a grid layout within the scrollable frame to
        #    align the checkboxes, labels, and uninstall buttons neatly in columns.

        for tool_name, is_installed in statuses.items():
            row = ctk.CTkFrame(self.cli_widgets_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            var = ctk.BooleanVar(value=is_installed)
            chk = ctk.CTkCheckBox(row, text=tool_name, variable=var)
            chk.pack(side="left")
            self.cli_vars[tool_name] = var

            if is_installed:
                ctk.CTkLabel(row, text="✅ Installed", text_color="green", width=100).pack(side="left", padx=10)
                chk.configure(state="disabled")
                
                # #TODO: Add uninstall functionality.
                # The application currently only supports installing tools. Adding
                # an uninstall feature would complete the lifecycle management.
                #
                # Suggested implementation:
                # 1. Add an "Uninstall" `CTkButton` here for each installed tool.
                # 2. Create a new method `uninstall_cli(tool_name)` that calls
                #    a corresponding `DevService.get_uninstall_cmd(tool_name)`.
                # 3. The service method should return the appropriate command
                #    (e.g., `npm uninstall -g <package>`).
                # 4. Run the command in a separate thread and provide feedback
                #    in the activity center, similar to the install process.
            else:
                ctk.CTkLabel(row, text="Not Installed", text_color="gray", width=120).pack(side="left", padx=10)

    def refresh_cli_list(self):
        # Clear and show loading
        for w in self.cli_widgets_frame.winfo_children(): w.destroy()
        ctk.CTkLabel(self.cli_widgets_frame, text="Checking installed tools...").pack(pady=10)

        def do_check():
            # In a thread, check all statuses
            DevService.clear_cache()
            statuses = {
                tool_name: DevService.is_installed(tool_name)
                for tool_name in DevService.CLI_MAP.keys()
            }
            # Schedule UI update on main thread
            self.app.after(0, lambda: self._update_cli_list_ui(statuses))

        threading.Thread(target=do_check, daemon=True).start()

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
                        # #TODO: Implement robust error handling and user feedback.
                        # The current implementation uses `subprocess.call` which blocks
                        # the thread and does not capture stdout/stderr. If an
                        # installation fails, the user receives no feedback beyond
                        # the progress bar stopping.
                        #
                        # Suggested implementation:
                        # 1. Use `subprocess.Popen` with `stdout=subprocess.PIPE` and
                        #    `stderr=subprocess.PIPE`.
                        # 2. Read the output streams in a separate thread to avoid deadlocks.
                        # 3. If the process returns a non-zero exit code, log the
                        #    error and display a user-friendly error message in a
                        #    message box or a dedicated log viewer in the UI.
                        # 4. Update the activity center to show a failure state.
                        subprocess.call(cmd, shell=(platform.system()=="Windows"))
                        self.app.update_activity(task_id, 1.0)
                    except Exception as e:
                        print(f"Install error: {e}")
                
                self.app.complete_activity(task_id)
            
            # Reset cache so UI can show 'Installed' status
            self.app.after(100, self.refresh_cli_list)
            
        threading.Thread(target=run, daemon=True).start()
        messagebox.showinfo("Started", "CLI installations started in the Activity Center.")
