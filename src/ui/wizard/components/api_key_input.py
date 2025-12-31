import customtkinter as ctk
import webbrowser
from src.services.dev_service import DevService

class ApiKeyInput(ctk.CTkFrame):
    def __init__(self, master, provider, api_key_name, api_key_url):
        super().__init__(master, fg_color="transparent")
        self.provider = provider
        
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(header, text=f"API Key Required ({api_key_name})", font=("Arial", 12, "bold")).pack(side="left")
        
        link = ctk.CTkLabel(header, text="Get Key ↗", font=("Arial", 11), text_color="#4cc9f0", cursor="hand2")
        link.pack(side="right")
        link.bind("<Button-1>", lambda e: webbrowser.open(api_key_url))
        
        self.entry = ctk.CTkEntry(self, placeholder_text=f"Paste {api_key_name} here...", width=300)
        self.entry.pack(fill="x", pady=5)
        
        self.status_lbl = ctk.CTkLabel(self, text="", font=("Arial", 10))
        self.status_lbl.pack(anchor="w")
        
        self.entry.bind("<KeyRelease>", self.on_change)
        
    def on_change(self, event=None):
        key = self.entry.get().strip()
        if len(key) > 10: # Basic length check
            valid = DevService.validate_api_key(self.provider, key)
            if valid:
                self.status_lbl.configure(text="✓ Valid API Key format", text_color="green")
            else:
                self.status_lbl.configure(text="⚠ Could not validate key (might still work)", text_color="orange")
        else:
            self.status_lbl.configure(text="", text_color="gray")

    def get_key(self):
        return self.entry.get().strip()
