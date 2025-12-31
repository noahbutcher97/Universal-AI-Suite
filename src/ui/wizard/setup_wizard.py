import customtkinter as ctk
import threading
from typing import List

from src.services.setup_wizard_service import SetupWizardService
from src.schemas.recommendation import UserProfile, ContentPreferences, CLIPreferences, ModuleRecommendation
from src.ui.wizard.components.use_case_card import UseCaseCard
from src.ui.wizard.components.module_config import ModuleConfig
from src.ui.wizard.components.progress_panel import ProgressPanel
from src.ui.wizard.components.experience_survey import ExperienceSurvey

class SetupWizard(ctk.CTkToplevel):
    def __init__(self, master, on_complete):
        super().__init__(master)
        self.on_complete_callback = on_complete
        self.service = SetupWizardService()
        
        self.title("AI Universal Suite - Setup Wizard")
        self.geometry("900x700")
        self.resizable(False, False)
        
        # State
        self.user_profile = UserProfile()
        self.selected_use_case_id = None
        self.current_recommendations: List[ModuleRecommendation] = []
        self.current_module_idx = 0
        self.manifest = None
        
        # UI Container
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Start
        self.service.start_wizard()
        self.show_welcome_stage()
        
        # Force focus
        self.after(100, self.lift)
        self.after(200, self.focus_force)

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    # --- Stage 1: Welcome & Use Case ---
    def show_welcome_stage(self):
        self.clear_container()
        
        ctk.CTkLabel(self.container, text="Welcome to AI Universal Suite", font=("Arial", 24, "bold")).pack(pady=(20, 10))
        ctk.CTkLabel(self.container, text="Select your primary goal to auto-configure your workstation.", font=("Arial", 14), text_color="gray70").pack(pady=(0, 30))
        
        grid = ctk.CTkFrame(self.container, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        
        cards = [
            ("content_generation", "Content Generation", "Generate images & video. Ideal for artists and designers.", "🎨"),
            ("productivity", "AI Productivity", "Coding & writing assistant. Ideal for developers and writers.", "⚡"),
            ("video_generation", "Video Generation", "Turn images into video clips. High-end hardware recommended.", "🎬"),
            ("full_stack", "Full AI Workstation", "Install everything. Complete creative and technical suite.", "🚀")
        ]
        
        self.use_case_cards = []
        
        for i, (uid, title, desc, icon) in enumerate(cards):
            card = UseCaseCard(grid, uid, title, desc, icon, command=self.on_use_case_selected)
            card.grid(row=i//2, column=i%2, padx=10, pady=10, sticky="nsew")
            self.use_case_cards.append(card)
            
        self.btn_next = ctk.CTkButton(self.container, text="Continue", state="disabled", command=self.show_experience_stage)
        self.btn_next.pack(side="bottom", pady=20, ipadx=20, ipady=5)

    def on_use_case_selected(self, use_case_id):
        self.selected_use_case_id = use_case_id
        for card in self.use_case_cards:
            card.set_selected(card.use_case_id == use_case_id)
        self.btn_next.configure(state="normal")
        
        # Pre-fill profile based on selection
        self.user_profile.primary_use_cases = [use_case_id]
        if use_case_id == "content_generation":
             self.user_profile.content_preferences["default"] = ContentPreferences(photorealism=4, generation_speed=3)
        elif use_case_id == "video_generation":
             self.user_profile.content_preferences["default"] = ContentPreferences(motion_intensity=4, temporal_coherence=5)
        elif use_case_id == "productivity":
             self.user_profile.cli_preferences = CLIPreferences(primary_tasks=["coding", "writing"])

    # --- Stage 1.5: Experience Survey ---
    def show_experience_stage(self):
        self.clear_container()
        ExperienceSurvey(self.container, self.on_experience_submitted).pack(fill="both", expand=True)
        
    def on_experience_submitted(self, ai_exp, tech_exp):
        self.user_profile.ai_experience = ai_exp
        self.user_profile.technical_experience = tech_exp
        
        # Calculate Proficiency
        avg = (ai_exp + tech_exp) / 2
        if avg <= 2: prof = "Beginner"
        elif avg <= 3: prof = "Intermediate"
        elif avg <= 4: prof = "Advanced"
        else: prof = "Expert"
        self.user_profile.proficiency = prof
        
        # Proceed
        self.start_scan()

    # --- Stage 2: Scanning ---
    def start_scan(self):
        self.clear_container()
        
        ctk.CTkLabel(self.container, text="Scanning Environment...", font=("Arial", 20, "bold")).pack(pady=50)
        
        progress = ctk.CTkProgressBar(self.container, mode="indeterminate")
        progress.pack(fill="x", padx=100)
        progress.start()
        
        self.status_lbl = ctk.CTkLabel(self.container, text="Detecting Hardware...", text_color="gray70")
        self.status_lbl.pack(pady=10)
        
        # Run scan in thread
        threading.Thread(target=self._run_scan, daemon=True).start()
        
    def _run_scan(self):
        # 1. System Scan
        env = self.service.scan_environment()
        
        # 2. Update UI
        self.after(0, lambda: self.status_lbl.configure(text=f"Found {env.gpu_name} ({env.vram_gb}GB VRAM)"))
        
        # 3. Generate Recommendations
        self.current_recommendations = self.service.generate_recommendations(self.selected_use_case_id, self.user_profile)
        
        # 4. Move to Modules
        self.current_module_idx = 0
        self.after(1500, self.show_next_module)

    # --- Stage 3: Module Config ---
    def show_next_module(self):
        if self.current_module_idx >= len(self.current_recommendations):
            self.show_review_stage()
            return
            
        rec = self.current_recommendations[self.current_module_idx]
        self.clear_container()
        
        # Step Indicator
        ctk.CTkLabel(self.container, text=f"Step {self.current_module_idx + 1} of {len(self.current_recommendations)}", text_color="gray60").pack(anchor="e")
        
        # Module Config Component
        self.current_config_ui = ModuleConfig(self.container, rec)
        self.current_config_ui.pack(fill="both", expand=True, pady=10)
        
        # Buttons
        btns = ctk.CTkFrame(self.container, fg_color="transparent")
        btns.pack(fill="x", pady=20)
        
        ctk.CTkButton(btns, text="Next", command=self.on_module_next).pack(side="right", padx=10)
        
    def on_module_next(self):
        # Save decision
        rec = self.current_recommendations[self.current_module_idx]
        
        if self.current_config_ui.is_enabled():
            overrides = self.current_config_ui.get_config_overrides()
            self.service.accept_module(rec.module_id, overrides)
        else:
            self.service.skip_module(rec.module_id)
            
        self.current_module_idx += 1
        self.show_next_module()

    # --- Stage 4: Review ---
    def show_review_stage(self):
        self.clear_container()
        self.manifest = self.service.generate_manifest()
        
        ctk.CTkLabel(self.container, text="Review Installation", font=("Arial", 20, "bold")).pack(pady=20)
        
        # Summary
        info = ctk.CTkFrame(self.container)
        info.pack(fill="x", pady=10)
        ctk.CTkLabel(info, text=f"Items to Install: {len(self.manifest.items)}", font=("Arial", 12, "bold")).pack(side="left", padx=20, pady=10)
        ctk.CTkLabel(info, text=f"Shortcuts: {len(self.manifest.shortcuts)}", font=("Arial", 12, "bold")).pack(side="right", padx=20, pady=10)
        
        # List
        scroll = ctk.CTkScrollableFrame(self.container, label_text="Installation Plan")
        scroll.pack(fill="both", expand=True, pady=10)
        
        for item in self.manifest.items:
            ctk.CTkLabel(scroll, text=f"• {item.name} ({item.item_type})", anchor="w").pack(fill="x", padx=5, pady=2)
            
        ctk.CTkButton(self.container, text="Begin Installation", fg_color="green", height=40, command=self.start_installation).pack(fill="x", pady=20)

    # --- Stage 5: Installation ---
    def start_installation(self):
        self.clear_container()
        
        ctk.CTkLabel(self.container, text="Installing...", font=("Arial", 20, "bold")).pack(pady=20)
        
        self.prog_panel = ProgressPanel(self.container)
        self.prog_panel.pack(fill="both", expand=True, pady=10)
        
        threading.Thread(target=self._run_install, daemon=True).start()
        
    def _run_install(self):
        success = self.service.execute_installation(
            self.manifest,
            progress_callback=self._on_progress,
            error_callback=self._on_error
        )
        
        if success:
            self.service.create_shortcuts(self.manifest)
            self.service.finalize()
            self.after(0, self.show_complete_stage)
        else:
            self.after(0, lambda: self.prog_panel.set_status("Installation Failed. See logs."))
            
    def _on_progress(self, item_name, progress):
        self.after(0, lambda: self.prog_panel.update_progress(item_name, progress))
        
    def _on_error(self, item_name, error):
        self.after(0, lambda: self.prog_panel.add_log(f"ERROR {item_name}: {error}"))

    # --- Stage 6: Complete ---
    def show_complete_stage(self):
        self.clear_container()
        
        ctk.CTkLabel(self.container, text="Setup Complete! 🎉", font=("Arial", 24, "bold"), text_color="green").pack(pady=50)
        ctk.CTkLabel(self.container, text="Your AI workstation is ready.", font=("Arial", 14)).pack(pady=10)
        
        ctk.CTkLabel(self.container, text="New shortcuts created on your Desktop.", text_color="gray70").pack(pady=20)
        
        ctk.CTkButton(self.container, text="Launch Dashboard", height=50, command=self.close_wizard).pack(fill="x", pady=50, padx=50)
        
    def close_wizard(self):
        self.destroy()
        if self.on_complete_callback:
            self.on_complete_callback()