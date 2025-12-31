import customtkinter as ctk
from tkinter import messagebox
from src.config.manager import config_manager

class SettingsFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        ctk.CTkLabel(self, text="Settings & Keys", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", pady=10)
        
        self.key_entries = {}
        
        # API Keys Section
        keys_frame = ctk.CTkFrame(self)
        keys_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(keys_frame, text="Secure API Key Vault", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        ctk.CTkLabel(keys_frame, text="Keys are stored securely in your OS Credential Manager.", text_color="gray").pack(anchor="w", padx=10, pady=(0, 10))

        for provider in config_manager.SECURE_KEYS:
            row = ctk.CTkFrame(keys_frame, fg_color="transparent")
            row.pack(fill="x", pady=5)
            
            ctk.CTkLabel(row, text=provider, width=150, anchor="w").pack(side="left", padx=10)
            ent = ctk.CTkEntry(row, show="*")
            ent.pack(side="left", fill="x", expand=True, padx=10)
            
            # Load existing
            val = config_manager.get_secure(provider)
            if val:
                ent.insert(0, val)
                
            self.key_entries[provider] = ent
            
        ctk.CTkButton(keys_frame, text="Save Keys", command=self.save_keys).pack(pady=20)
        
        # System Section
        sys_frame = ctk.CTkFrame(self)
        sys_frame.pack(fill="x", pady=20)
        ctk.CTkLabel(sys_frame, text="System & Maintenance", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkButton(sys_frame, text="Re-run Setup Wizard", fg_color="#555555", command=self.rerun_wizard).pack(anchor="w", padx=20, pady=20)

    def save_keys(self):
        for k, ent in self.key_entries.items():
            val = ent.get().strip()
            if val:
                config_manager.set_secure(k, val)
            
        messagebox.showinfo("Saved", "API Keys saved securely to OS Keychain.")

    def rerun_wizard(self):
        if messagebox.askyesno("Confirm", "This will re-scan your system and may overwrite existing configurations. Continue?"):
            self.app.show_setup_wizard()