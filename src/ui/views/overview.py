import customtkinter as ctk
import platform
from src.services.system_service import SystemService

class OverviewFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        title = ctk.CTkLabel(self, text="System Status", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(anchor="w", pady=10)
        
        info_card = ctk.CTkFrame(self)
        info_card.pack(fill="x", pady=10)
        
        # System Info
        gpu_vendor, gpu_name, vram = SystemService.get_gpu_info()
        os_name = platform.system()
        
        ctk.CTkLabel(info_card, text=f"OS: {os_name}").pack(side="left", padx=20, pady=15)
        ctk.CTkLabel(info_card, text=f"GPU: {gpu_name}").pack(side="left", padx=20, pady=15)
        ctk.CTkLabel(info_card, text=f"VRAM: {vram:.1f} GB").pack(side="left", padx=20, pady=15)

        # Env Checks (Quick View)
        env = SystemService.verify_environment()
        env_card = ctk.CTkFrame(self)
        env_card.pack(fill="x", pady=10)
        ctk.CTkLabel(env_card, text="Environment Health:", font=("Arial", 14, "bold")).pack(anchor="w", padx=20, pady=10)
        
        for tool, available in env.items():
            color = "green" if available else "red"
            icon = "✅" if available else "❌"
            ctk.CTkLabel(env_card, text=f"{icon} {tool.upper()}", text_color=color).pack(side="left", padx=20, pady=10)