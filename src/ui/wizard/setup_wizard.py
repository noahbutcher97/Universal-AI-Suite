"""
Setup Wizard - Generation Focus MVP.

Per PLAN: Generation Focus MVP - This wizard guides users through:
1. Journey selection (Express/Explore)
2. Experience survey (AI experience, cloud preferences, cost sensitivity)
3. Hardware scan
4. Capability selection (what modalities to generate)
5. Model selection (with comparison lenses)
6. CLI provider selection
7. Review and install
"""

import customtkinter as ctk
import threading
from typing import List, Dict, Optional

from src.services.setup_wizard_service import SetupWizardService
from src.schemas.recommendation import (
    UserProfile,
    ContentPreferences,
    CLIPreferences,
    CloudAPIPreferences,
    RecommendationResults,
    ModelCandidate,
    CloudRankedCandidate,
    RankedCandidate
)
from src.schemas.environment import EnvironmentReport
from src.schemas.hardware import HardwareProfile, PlatformType
from src.ui.wizard.components.capability_selector import CapabilitySelector
from src.ui.wizard.components.model_comparison import ModelComparisonView
from src.ui.wizard.components.progress_panel import ProgressPanel
from src.ui.wizard.components.experience_survey import ExperienceSurvey
from src.utils.logger import log
from src.utils.performance_monitor import get_performance_monitor


class SetupWizard(ctk.CTkToplevel):
    """
    Main setup wizard window.

    Guides users through AI workstation configuration with:
    - Hardware-aware model recommendations
    - Cloud/local preference support
    - Comparison lenses for informed decisions
    """

    def __init__(self, master, on_complete):
        super().__init__(master)
        self.on_complete_callback = on_complete
        self.service = SetupWizardService()

        self.title("AI Universal Suite - Setup Wizard")
        self.geometry("900x700")
        self.resizable(False, False)

        # State
        self.user_profile = UserProfile()
        self.selected_modalities: List[str] = []
        self.recommendation_results: Optional[RecommendationResults] = None
        self.selected_local_models: List[str] = []
        self.selected_cloud_models: List[str] = []
        self.env_report: Optional[EnvironmentReport] = None
        self.hardware_profile: Optional[HardwareProfile] = None
        self.manifest = None

        # UI Container
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=20)

        # Start
        self.service.start_wizard()
        self.show_journey_stage()

        # Force focus
        self.after(100, self.lift)
        self.after(200, self.focus_force)

    def clear_container(self):
        """Clear all widgets from the container."""
        for widget in self.container.winfo_children():
            widget.destroy()

    # --- Stage 1: Journey Selection ---
    def show_journey_stage(self):
        """Show journey selection: Express Setup vs Explore First."""
        self.clear_container()

        ctk.CTkLabel(
            self.container,
            text="Welcome to AI Universal Suite",
            font=("Arial", 24, "bold")
        ).pack(pady=(40, 10))

        ctk.CTkLabel(
            self.container,
            text="How would you like to set up your AI workstation?",
            font=("Arial", 14),
            text_color="gray70"
        ).pack(pady=(0, 40))

        # Journey cards
        cards_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        cards_frame.pack(fill="x", padx=50)
        cards_frame.grid_columnconfigure(0, weight=1)
        cards_frame.grid_columnconfigure(1, weight=1)

        # Express Setup
        express_card = ctk.CTkFrame(cards_frame, corner_radius=10)
        express_card.grid(row=0, column=0, padx=15, pady=10, sticky="nsew")

        ctk.CTkLabel(
            express_card,
            text="⚡",
            font=("Arial", 40)
        ).pack(pady=(30, 10))

        ctk.CTkLabel(
            express_card,
            text="Express Setup",
            font=("Arial", 18, "bold")
        ).pack()

        ctk.CTkLabel(
            express_card,
            text="Quick guided setup with\nrecommended defaults",
            font=("Arial", 12),
            text_color="gray70",
            justify="center"
        ).pack(pady=(5, 20))

        ctk.CTkButton(
            express_card,
            text="Start Express Setup",
            command=self.show_experience_stage,
            height=40
        ).pack(pady=(0, 30), padx=30, fill="x")

        # Explore First
        explore_card = ctk.CTkFrame(cards_frame, corner_radius=10)
        explore_card.grid(row=0, column=1, padx=15, pady=10, sticky="nsew")

        ctk.CTkLabel(
            explore_card,
            text="🔍",
            font=("Arial", 40)
        ).pack(pady=(30, 10))

        ctk.CTkLabel(
            explore_card,
            text="Explore First",
            font=("Arial", 18, "bold")
        ).pack()

        ctk.CTkLabel(
            explore_card,
            text="Browse capabilities and\nmodels before deciding",
            font=("Arial", 12),
            text_color="gray70",
            justify="center"
        ).pack(pady=(5, 20))

        ctk.CTkButton(
            explore_card,
            text="Start Exploring",
            # TODO: Implement differentiated Explore First flow (hub-and-spoke browsing)
            # Currently both paths use the same flow - Explore First should eventually
            # skip to capability browsing before the survey, allowing users to see
            # what's possible before committing to preferences.
            command=self.show_experience_stage,
            fg_color="gray30",
            hover_color="gray40",
            height=40
        ).pack(pady=(0, 30), padx=30, fill="x")

    # --- Stage 2: Experience Survey ---
    def show_experience_stage(self):
        """Show experience and preference survey."""
        self.clear_container()

        # Get storage info for contextual warning
        storage_free_gb = self._get_storage_free_gb()

        ExperienceSurvey(
            self.container,
            self.on_experience_submitted,
            storage_free_gb=storage_free_gb
        ).pack(fill="both", expand=True)

    def _get_storage_free_gb(self) -> float:
        """Get free storage space in GB for survey context."""
        try:
            import shutil
            total, used, free = shutil.disk_usage(".")
            return free / (1024 ** 3)
        except Exception:
            return 100.0

    def on_experience_submitted(
        self,
        ai_exp: int,
        tech_exp: int,
        cloud_willingness: str = "cloud_fallback",
        cost_sensitivity: int = 3
    ):
        """Handle survey submission."""
        self.user_profile.ai_experience = ai_exp
        self.user_profile.technical_experience = tech_exp

        # Calculate proficiency
        avg = (ai_exp + tech_exp) / 2
        if avg <= 2:
            prof = "Beginner"
        elif avg <= 3:
            prof = "Intermediate"
        elif avg <= 4:
            prof = "Advanced"
        else:
            prof = "Expert"
        self.user_profile.proficiency = prof

        # Set cloud preferences
        self.user_profile.cloud_api_preferences = CloudAPIPreferences(
            cloud_willingness=cloud_willingness,
            cost_sensitivity=cost_sensitivity
        )

        log.info(
            f"User profile configured: proficiency={prof}, "
            f"cloud_willingness={cloud_willingness}, cost_sensitivity={cost_sensitivity}"
        )

        # Proceed to hardware scan
        self.start_scan()

    # --- Stage 3: Hardware Scan ---
    def start_scan(self):
        """Start hardware scanning."""
        self.clear_container()

        ctk.CTkLabel(
            self.container,
            text="Scanning Your System...",
            font=("Arial", 20, "bold")
        ).pack(pady=50)

        progress = ctk.CTkProgressBar(self.container, mode="indeterminate")
        progress.pack(fill="x", padx=100)
        progress.start()

        self.status_lbl = ctk.CTkLabel(
            self.container,
            text="Detecting hardware...",
            text_color="gray70"
        )
        self.status_lbl.pack(pady=10)

        # Run scan in thread
        threading.Thread(target=self._run_scan, daemon=True).start()

    def _run_scan(self):
        """Run hardware scan in background."""
        log.info("Starting environment scan")
        env = self.service.scan_environment()

        # Store environment report
        self.env_report = env

        # Create proper HardwareProfile from EnvironmentReport
        self.hardware_profile = self._create_hardware_profile(env)

        log.info(
            f"Environment scan complete: GPU={env.gpu_name}, "
            f"VRAM={env.vram_gb}GB, OS={env.os_name}"
        )

        # Update UI
        self.after(
            0,
            lambda: self.status_lbl.configure(
                text=f"Found {env.gpu_name} ({env.vram_gb}GB VRAM)"
            )
        )

        # Move to capability selection
        self.after(1500, self.show_capability_stage)

    def _create_hardware_profile(self, env: EnvironmentReport) -> HardwareProfile:
        """Create a HardwareProfile from EnvironmentReport."""
        # Determine platform type from environment
        platform = self._detect_platform_type(env)

        # Determine if unified memory (Apple Silicon)
        unified_memory = env.gpu_vendor == "apple"

        # Parse compute capability if available
        compute_capability = None
        if env.cuda_compute_capability:
            try:
                compute_capability = float(env.cuda_compute_capability)
            except (ValueError, TypeError):
                pass

        return HardwareProfile(
            platform=platform,
            gpu_vendor=env.gpu_vendor,
            gpu_name=env.gpu_name,
            vram_gb=env.vram_gb,
            unified_memory=unified_memory,
            compute_capability=compute_capability,
            supports_fp8=compute_capability is not None and compute_capability >= 8.9,
            supports_bf16=compute_capability is not None and compute_capability >= 8.0,
            supports_tf32=compute_capability is not None and compute_capability >= 8.0,
            flash_attention_available=compute_capability is not None and compute_capability >= 8.0,
            gpu_count=env.gpu_count,
            gpu_bandwidth_gbps=env.gpu_memory_bandwidth_gbps,
        )

    def _detect_platform_type(self, env: EnvironmentReport) -> PlatformType:
        """Detect PlatformType from EnvironmentReport."""
        if env.gpu_vendor == "apple":
            return PlatformType.APPLE_SILICON
        elif env.gpu_vendor == "nvidia":
            if env.os_name == "Windows":
                return PlatformType.WINDOWS_NVIDIA
            elif env.os_name == "Linux":
                # Check for WSL
                try:
                    with open("/proc/version", "r") as f:
                        if "microsoft" in f.read().lower():
                            return PlatformType.WSL2_NVIDIA
                except (FileNotFoundError, PermissionError):
                    pass
                return PlatformType.LINUX_NVIDIA
        elif env.gpu_vendor == "amd":
            return PlatformType.LINUX_ROCM
        elif env.gpu_vendor == "none" or env.vram_gb == 0:
            return PlatformType.CPU_ONLY
        return PlatformType.UNKNOWN

    # --- Stage 4: Capability Selection ---
    def show_capability_stage(self):
        """Show modality/capability selection."""
        self.clear_container()

        cloud_willingness = self.user_profile.cloud_api_preferences.cloud_willingness

        selector = CapabilitySelector(
            self.container,
            hardware_profile=self.hardware_profile,
            cloud_willingness=cloud_willingness,
            on_selection_change=self._on_capability_change
        )
        selector.pack(fill="both", expand=True)

        # Store reference for getting selections
        self.capability_selector = selector

        # Navigation buttons
        btn_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)

        ctk.CTkButton(
            btn_frame,
            text="Back",
            fg_color="gray30",
            hover_color="gray40",
            command=self.show_experience_stage
        ).pack(side="left")

        self.btn_next_capability = ctk.CTkButton(
            btn_frame,
            text="Continue",
            command=self.on_capability_continue
        )
        self.btn_next_capability.pack(side="right")

    def _on_capability_change(self, selected: List[str]):
        """Handle capability selection change."""
        self.selected_modalities = selected
        # Enable/disable continue button
        if hasattr(self, 'btn_next_capability'):
            state = "normal" if selected else "disabled"
            self.btn_next_capability.configure(state=state)

    def on_capability_continue(self):
        """Continue from capability selection to model selection."""
        self.selected_modalities = self.capability_selector.get_selected_modalities()

        if not self.selected_modalities:
            # Show error - must select at least one
            return

        log.info(f"Selected modalities: {self.selected_modalities}")

        # Generate recommendations
        self.show_loading_recommendations()

    def show_loading_recommendations(self):
        """Show loading state while generating recommendations."""
        self.clear_container()

        ctk.CTkLabel(
            self.container,
            text="Finding the Best Models for You...",
            font=("Arial", 20, "bold")
        ).pack(pady=50)

        progress = ctk.CTkProgressBar(self.container, mode="indeterminate")
        progress.pack(fill="x", padx=100)
        progress.start()

        self.status_lbl = ctk.CTkLabel(
            self.container,
            text="Analyzing models and APIs...",
            text_color="gray70"
        )
        self.status_lbl.pack(pady=10)

        # Run recommendation generation in thread
        threading.Thread(target=self._run_recommendations, daemon=True).start()

    def _run_recommendations(self):
        """Generate recommendations in background."""
        try:
            log.info(
                f"Generating parallel recommendations for modalities: "
                f"{self.selected_modalities}"
            )

            # Map modalities to categories for the recommendation engine
            category_map = {
                "image": ["image_generation", "image_editing"],
                "video": ["video_generation"],
                "audio": ["audio_generation"],
                "text": ["text_generation"],
                "3d": ["3d_generation"],
            }

            categories = []
            for modality in self.selected_modalities:
                for cat in category_map.get(modality, []):
                    if cat not in categories:
                        categories.append(cat)

            # Generate recommendations using new parallel pathway
            self.recommendation_results = self.service.recommendation_service.generate_parallel_recommendations(
                user_profile=self.user_profile,
                env=self.service.env_report,
                categories=categories if categories else None
            )

            log.info(
                f"Generated {len(self.recommendation_results.local_recommendations)} local "
                f"and {len(self.recommendation_results.cloud_recommendations)} cloud recommendations"
            )

            # Move to model selection
            self.after(0, self.show_model_selection_stage)
        except Exception as e:
            log.exception(f"Error in recommendation thread: {e}")
            err_str = str(e)
            self.after(0, lambda: self._show_recommendation_error(err_str))

    def _show_recommendation_error(self, error_msg: str):
        """Show error message if recommendation fails."""
        self.clear_container()
        
        ctk.CTkLabel(
            self.container,
            text="Oops! Something went wrong while finding models.",
            font=("Arial", 18, "bold"),
            text_color="#ff4444"
        ).pack(pady=(50, 20))
        
        ctk.CTkLabel(
            self.container,
            text=f"Error details: {error_msg}",
            text_color="gray70",
            wraplength=600
        ).pack(pady=10)
        
        ctk.CTkButton(
            self.container,
            text="Try Again",
            command=self.show_loading_recommendations
        ).pack(pady=30)
        
        ctk.CTkButton(
            self.container,
            text="Back",
            fg_color="gray30",
            hover_color="gray40",
            command=self.show_capability_stage
        ).pack()

    # --- Stage 5: Model Selection ---
    def show_model_selection_stage(self):
        """Show model comparison and selection view."""
        self.clear_container()

        if not self.recommendation_results:
            # No results - show error
            ctk.CTkLabel(
                self.container,
                text="No models found for your configuration.",
                font=("Arial", 16),
                text_color="gray60"
            ).pack(pady=50)
            return

        cloud_willingness = self.user_profile.cloud_api_preferences.cloud_willingness

        comparison_view = ModelComparisonView(
            self.container,
            results=self.recommendation_results,
            selected_modalities=self.selected_modalities,
            cloud_willingness=cloud_willingness,
            on_selection_change=self._on_model_selection_change
        )
        comparison_view.pack(fill="both", expand=True)

        # Store reference
        self.model_comparison_view = comparison_view

        # Navigation buttons
        btn_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)

        ctk.CTkButton(
            btn_frame,
            text="Back",
            fg_color="gray30",
            hover_color="gray40",
            command=self.show_capability_stage
        ).pack(side="left")

        self.btn_next_models = ctk.CTkButton(
            btn_frame,
            text="Continue",
            command=self.on_model_selection_continue
        )
        self.btn_next_models.pack(side="right")

    def _on_model_selection_change(
        self,
        local_selected: List[str],
        cloud_selected: List[str]
    ):
        """Handle model selection change."""
        self.selected_local_models = local_selected
        self.selected_cloud_models = cloud_selected

    def on_model_selection_continue(self):
        """Continue from model selection."""
        selected = self.model_comparison_view.get_selected_models()
        self.selected_local_models = selected.get("local", [])
        self.selected_cloud_models = selected.get("cloud", [])

        log.info(
            f"Selected models - Local: {self.selected_local_models}, "
            f"Cloud: {self.selected_cloud_models}"
        )

        # For MVP: Go directly to review (skip CLI selection)
        # TODO: Add CLI provider selection stage
        self.show_review_stage()

    # --- Stage 6: Review ---
    def show_review_stage(self):
        """Show installation review."""
        self.clear_container()

        ctk.CTkLabel(
            self.container,
            text="Review Your Setup",
            font=("Arial", 20, "bold")
        ).pack(pady=20)

        # Summary frame
        summary = ctk.CTkFrame(self.container)
        summary.pack(fill="x", pady=10, padx=20)

        # Local models summary
        if self.selected_local_models:
            ctk.CTkLabel(
                summary,
                text=f"💻 Local Models: {len(self.selected_local_models)}",
                font=("Arial", 14, "bold"),
                anchor="w"
            ).pack(fill="x", padx=15, pady=(15, 5))

            for model_id in self.selected_local_models[:5]:
                ctk.CTkLabel(
                    summary,
                    text=f"  • {model_id}",
                    font=("Arial", 12),
                    text_color="gray70",
                    anchor="w"
                ).pack(fill="x", padx=15)

            if len(self.selected_local_models) > 5:
                ctk.CTkLabel(
                    summary,
                    text=f"  ... and {len(self.selected_local_models) - 5} more",
                    font=("Arial", 11),
                    text_color="gray60",
                    anchor="w"
                ).pack(fill="x", padx=15)

        # Cloud models summary
        if self.selected_cloud_models:
            ctk.CTkLabel(
                summary,
                text=f"☁ Cloud APIs: {len(self.selected_cloud_models)}",
                font=("Arial", 14, "bold"),
                anchor="w"
            ).pack(fill="x", padx=15, pady=(15, 5))

            for model_id in self.selected_cloud_models[:5]:
                ctk.CTkLabel(
                    summary,
                    text=f"  • {model_id}",
                    font=("Arial", 12),
                    text_color="gray70",
                    anchor="w"
                ).pack(fill="x", padx=15)

        # Empty state
        if not self.selected_local_models and not self.selected_cloud_models:
            ctk.CTkLabel(
                summary,
                text="No models selected. Go back to select models.",
                font=("Arial", 12),
                text_color="gray60"
            ).pack(pady=20)

        # Padding
        ctk.CTkFrame(summary, height=15, fg_color="transparent").pack()

        # Navigation
        btn_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20, padx=20)

        ctk.CTkButton(
            btn_frame,
            text="Back",
            fg_color="gray30",
            hover_color="gray40",
            command=self.show_model_selection_stage
        ).pack(side="left")

        if self.selected_local_models or self.selected_cloud_models:
            ctk.CTkButton(
                btn_frame,
                text="Begin Installation",
                fg_color="green",
                hover_color="#166534",
                command=self.start_installation
            ).pack(side="right")

    # --- Stage 7: Installation ---
    def start_installation(self):
        """Start the installation process."""
        self.clear_container()

        ctk.CTkLabel(
            self.container,
            text="Installing...",
            font=("Arial", 20, "bold")
        ).pack(pady=20)

        self.prog_panel = ProgressPanel(self.container)
        self.prog_panel.pack(fill="both", expand=True, pady=10)

        threading.Thread(target=self._run_install, daemon=True).start()

    def _run_install(self):
        """Run installation in background."""
        log.info("Starting real installation planning...")

        # 1. Map selected IDs back to objects
        selected_objs = [
            r for r in self.recommendation_results.local_recommendations
            if r.id in self.selected_local_models
        ]

        # 2. Generate full manifest (VAEs, Nodes, Encoders)
        manifest = self.service.recommendation_service.generate_full_manifest(
            self.user_profile,
            selected_objs
        )

        log.info(f"Generated manifest with {len(manifest.items)} items. Total size: {manifest.total_size_gb:.1f}GB")

        # 3. Execute installation via service
        success = self.service.execute_installation(
            manifest,
            progress_callback=self._on_progress,
            error_callback=self._on_error
        )

        if success:
            self.service.finalize()
            self.after(0, self.show_complete_stage)
        else:
            log.error("Installation failed for some items.")
            # Still show completion but maybe with warnings
            self.after(0, self.show_complete_stage)

    def _on_progress(self, item_name: str, progress: float):
        """Handle installation progress update."""
        self.after(0, lambda: self.prog_panel.update_progress(item_name, progress))

    def _on_error(self, item_name: str, error: Exception):
        """Handle installation error."""
        self.after(0, lambda: self.prog_panel.add_log(f"ERROR {item_name}: {error}"))

    # --- Stage 8: Complete ---
    def show_complete_stage(self):
        """Show completion screen."""
        self.clear_container()

        ctk.CTkLabel(
            self.container,
            text="Setup Complete!",
            font=("Arial", 24, "bold"),
            text_color="#22c55e"
        ).pack(pady=50)

        ctk.CTkLabel(
            self.container,
            text="Your AI workstation is ready.",
            font=("Arial", 14)
        ).pack(pady=10)

        # Summary
        local_count = len(self.selected_local_models)
        cloud_count = len(self.selected_cloud_models)

        if local_count or cloud_count:
            summary_parts = []
            if local_count:
                summary_parts.append(f"{local_count} local model(s)")
            if cloud_count:
                summary_parts.append(f"{cloud_count} cloud API(s)")

            ctk.CTkLabel(
                self.container,
                text=f"Configured: {' and '.join(summary_parts)}",
                font=("Arial", 12),
                text_color="gray70"
            ).pack(pady=5)

        ctk.CTkButton(
            self.container,
            text="Launch Dashboard",
            height=50,
            command=self.close_wizard
        ).pack(fill="x", pady=50, padx=100)

    def close_wizard(self):
        """Close wizard and trigger completion callback."""
        get_performance_monitor().save_report()
        self.destroy()
        if self.on_complete_callback:
            self.on_complete_callback()
