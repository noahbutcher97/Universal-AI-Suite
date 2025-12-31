import customtkinter as ctk
from src.schemas.recommendation import ModuleRecommendation
from src.ui.wizard.components.reasoning_display import ReasoningDisplay
from src.ui.wizard.components.warning_banner import WarningBanner
from src.ui.wizard.components.api_key_input import ApiKeyInput
from src.services.dev_service import DevService # For provider details lookup

class ModuleConfig(ctk.CTkFrame):
    def __init__(self, master, recommendation: ModuleRecommendation):
        super().__init__(master)
        self.recommendation = recommendation
        self.api_key_input = None
        
        # Header
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(head, text=recommendation.display_name, font=("Arial", 18, "bold")).pack(side="left")
        
        # Enable Toggle (Skip/Install)
        self.var_enabled = ctk.BooleanVar(value=recommendation.enabled)
        self.switch = ctk.CTkSwitch(head, text="Install", variable=self.var_enabled)
        self.switch.pack(side="right")
        
        # Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        ctk.CTkLabel(body, text=recommendation.description, font=("Arial", 12), text_color="gray80", wraplength=500, justify="left").pack(anchor="w", pady=(0, 10))
        
        # Warnings
        if recommendation.warnings:
            WarningBanner(body, recommendation.warnings).pack(fill="x", pady=5)
            
        # Reasoning
        ReasoningDisplay(body, recommendation.reasoning).pack(fill="x", pady=10)
        
        # Config (Specifics)
        conf_frame = ctk.CTkFrame(body, fg_color="#2b2b2b")
        conf_frame.pack(fill="x", pady=10, ipady=5)
        
        if recommendation.module_id == "comfyui":
            self._build_comfy_config(conf_frame, recommendation.config)
        elif recommendation.module_id == "cli_provider":
            self._build_cli_config(conf_frame, recommendation.config)
            
        # Stats
        stats = ctk.CTkLabel(body, text=f"Est. Size: {recommendation.estimated_size_gb:.1f} GB  •  Time: ~{recommendation.estimated_time_minutes} min", text_color="gray60", font=("Arial", 11))
        stats.pack(anchor="e", pady=5)

    def _build_comfy_config(self, parent, config):
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(grid, text="Model Tier:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", padx=5)
        ctk.CTkLabel(grid, text=config.get("model_tier", "Unknown").upper()).grid(row=0, column=1, sticky="w", padx=5)
        
        ctk.CTkLabel(grid, text="Selected Model:", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky="w", padx=5)
        ctk.CTkLabel(grid, text=config.get("selected_model", "None")).grid(row=1, column=1, sticky="w", padx=5)

    def _build_cli_config(self, parent, config):
        provider = config.get("provider", "gemini")
        # Lookup provider details for API Key info
        prov_info = DevService.get_provider_config(provider)
        
        if prov_info and prov_info.get("api_key_name"):
            self.api_key_input = ApiKeyInput(
                parent, 
                provider, 
                prov_info["api_key_name"], 
                prov_info["api_key_url"]
            )
            self.api_key_input.pack(fill="x", padx=10, pady=5)
        else:
            ctk.CTkLabel(parent, text=f"Provider: {provider.capitalize()}", padx=10).pack(anchor="w")

    def get_config_overrides(self):
        overrides = {}
        if self.api_key_input:
            key = self.api_key_input.get_key()
            if key:
                overrides["api_key"] = key
        return overrides
        
    def is_enabled(self):
        return self.var_enabled.get()
