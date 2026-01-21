"""
Model Card Component for the Setup Wizard.

Per PLAN: Generation Focus MVP - This component displays individual model
recommendations with compact and expanded views, supporting progressive reveal.

Badges reflect recommendation fit (hardware, cost, preferences), not static
model architecture names.
"""

import customtkinter as ctk
from typing import Optional, Callable, List, Union
from dataclasses import dataclass

from src.schemas.recommendation import ModelCandidate, CloudRankedCandidate
from src.utils.performance_monitor import measure_time


def _format_size(size_gb: float) -> str:
    """Format file size for display."""
    if size_gb >= 1.0:
        return f"{size_gb:.1f} GB"
    else:
        return f"{int(size_gb * 1024)} MB"


@dataclass
class FitBadge:
    """Badge configuration based on fit score."""
    text: str
    fg_color: str
    text_color: str = "white"


def _get_hardware_fit_badge(score: float) -> FitBadge:
    """
    Get badge based on hardware fit score.

    Score ranges (0.0-1.0):
    - 0.8+: Perfect fit for user's hardware
    - 0.6-0.8: Good fit, may need minor adjustments
    - 0.4-0.6: Possible with optimizations (quantization, offload)
    - <0.4: May struggle on user's hardware
    """
    if score >= 0.8:
        return FitBadge("Perfect Fit", "#166534")  # Green
    elif score >= 0.6:
        return FitBadge("Good Fit", "#1e40af")  # Blue
    elif score >= 0.4:
        return FitBadge("Needs Optimization", "#b45309")  # Amber
    else:
        return FitBadge("May Struggle", "#991b1b")  # Red


def _get_cost_badge(cost_score: float, is_cloud: bool) -> Optional[FitBadge]:
    """
    Get badge based on cost efficiency score.

    For cloud: cost_score is inverse of price (higher = cheaper)
    For local: cost_score can represent size efficiency
    """
    if not is_cloud:
        return None  # Local models show size instead

    if cost_score >= 0.7:
        return FitBadge("Budget", "#166534")  # Green
    elif cost_score >= 0.4:
        return FitBadge("Standard", "#1e40af")  # Blue
    else:
        return FitBadge("Premium", "#7c3aed")  # Purple


def _get_match_badge(overall_score: float) -> FitBadge:
    """
    Get badge based on overall recommendation match.

    This is the composite score from the recommendation engine.
    """
    if overall_score >= 0.8:
        return FitBadge("★ Best Match", "#854d0e", "#fbbf24")  # Gold on dark
    elif overall_score >= 0.6:
        return FitBadge("Strong Match", "#1e40af")
    elif overall_score >= 0.4:
        return FitBadge("Compatible", "#4b5563")  # Gray
    else:
        return FitBadge("Partial Match", "#6b7280")


class ModelCard(ctk.CTkFrame):
    """
    A model recommendation card with compact and expanded views.

    Supports both local (ModelCandidate) and cloud (CloudRankedCandidate) models.
    Features progressive reveal - starts compact, expands on user request.

    Badges are dynamic based on recommendation scores:
    - Hardware fit: How well model runs on user's hardware
    - Cost efficiency: Budget/Standard/Premium for cloud models
    - Overall match: How well model matches user's preferences
    """

    @measure_time("ModelCard.__init__")
    def __init__(
        self,
        master,
        model: Union[ModelCandidate, CloudRankedCandidate],
        is_cloud: bool = False,
        is_recommended: bool = False,
        on_select: Callable[[str, bool], None] = None
    ):
        super().__init__(master, corner_radius=10, border_width=1, border_color="gray30")

        self.model = model
        self.is_cloud = is_cloud
        self.is_recommended = is_recommended
        self.on_select = on_select
        self.expanded = False
        self.expanded_frame = None

        # Extract common properties based on model type
        if is_cloud:
            self.model_id = model.model_id
            self.display_name = model.display_name
            self.overall_score = model.overall_score
            self.provider = model.provider
            self.reasoning = model.reasoning
            self.hardware_fit_score = 1.0  # Cloud doesn't need hardware fit
            self.cost_score = model.cost_score
        else:
            self.model_id = model.id
            self.display_name = model.display_name
            self.overall_score = model.composite_score
            self.reasoning = model.reasoning
            self.hardware_fit_score = getattr(model, 'hardware_fit_score', 0.5)
            self.cost_score = 0.0  # Not applicable for local

        # Selection state - always start unselected, let parent restore from persistent state
        self.var_selected = ctk.BooleanVar(value=False)

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the complete UI (called on init and rebuild)."""
        # Clear any existing widgets
        for widget in self.winfo_children():
            widget.destroy()

        self._build_compact_view()
        # Expanded view is now built lazily in _toggle_expand

    def _build_compact_view(self):
        """Build the always-visible compact view (Flattened Layout)."""
        self.grid_columnconfigure(1, weight=1)

        # 1. Checkbox (Row 0-1, Col 0)
        self.checkbox = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.var_selected,
            command=self._on_toggle,
            width=24,
            height=24
        )
        self.checkbox.grid(row=0, column=0, rowspan=2, padx=(15, 10), pady=12, sticky="ns")

        # 2. Name & Badges (Row 0, Col 1)
        # We combine Name + Badges into a single frame to keep alignment, 
        # OR we just make the name the label and badges separate.
        # To strictly flatten, we can put Name in col 1, Badges in col 2? No, badges vary.
        # Let's keep one frame for Name/Badges but make it very lightweight.
        
        # Actually, let's try strict grid on self.
        # Name: (0, 1)
        # Stats: (1, 1)
        # Expand: (0-1, 2)
        
        self.name_label = ctk.CTkLabel(
            self,
            text=self.display_name,
            font=("Arial", 14, "bold"),
            anchor="w"
        )
        self.name_label.grid(row=0, column=1, sticky="w", pady=(12, 0))

        # 3. Stats (Row 1, Col 1)
        stats_text = self._get_stats_text()
        self.stats_label = ctk.CTkLabel(
            self,
            text=stats_text,
            font=("Arial", 11),
            text_color="gray60",
            anchor="w"
        )
        self.stats_label.grid(row=1, column=1, sticky="w", pady=(0, 12))

        # 4. Badges (Row 0, Col 1 - Defer to next frame for speed)
        self.after(1, lambda: self._add_badges_to_grid(row=0, column=1))

        # 5. Expand Button (Row 0-1, Col 2)
        self.expand_btn = ctk.CTkButton(
            self,
            text="▼",
            width=30,
            height=28,
            fg_color="transparent",
            hover_color="gray25",
            text_color="gray60",
            command=self._toggle_expand
        )
        self.expand_btn.grid(row=0, column=2, rowspan=2, padx=(10, 15), pady=12)

    def _add_badges_to_grid(self, row, column):
        """Add badges to the grid layout, offset from name."""
        # This is tricky without a nested frame. 
        # Let's use a nested frame but ensure it's the ONLY one.
        # Actually, let's put badges in the same cell as Name but use a Frame container for THAT cell.
        # Wait, I promised to flatten.
        # If I put Name and Badges in one Frame, that is 1 Frame + N Widgets.
        # Previous: CompactFrame -> NameRow -> [Name, Badge, Badge]
        # Current: ModelCard -> HeaderFrame -> [Name, Badge, Badge]
        # It removes one layer (CompactFrame).
        
        # Let's try simpler: Put Name in grid. Put Badges in a Frame that is placed via place() or grid() next to it?
        # No, dynamic width name makes that hard.
        
        # Compromise: HeaderFrame is necessary for horizontal layout of Name + Badges.
        # But we remove StatsFrame and CompactFrame.
        
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=1, sticky="w", pady=(12, 0))
        
        ctk.CTkLabel(
            header_frame,
            text=self.display_name,
            font=("Arial", 14, "bold")
        ).pack(side="left")
        
        self._add_dynamic_badges(header_frame)

    def _get_stats_text(self) -> str:
        """Get combined stats text."""
        parts = []
        
        if self.is_cloud:
            model_cloud = self.model
            parts.append(f"${model_cloud.estimated_cost_per_use:.3f}/gen")
            if model_cloud.estimated_monthly_cost > 0:
                parts.append(f"~${model_cloud.estimated_monthly_cost:.0f}/mo")
        else:
            model_local = self.model
            reqs = getattr(model_local, 'requirements', {})
            size_gb = reqs.get('size_gb', 0)
            vram_min = reqs.get('vram_min_gb', 0) or (reqs.get('vram_min_mb', 0) / 1024)
            
            if size_gb > 0:
                parts.append(_format_size(size_gb))
            if vram_min > 0:
                parts.append(f"≥{vram_min:.0f}GB VRAM")
                
        parts.append(f"Match: {self.overall_score:.0%}")
        return "  •  ".join(parts)

    def _add_dynamic_badges(self, parent):
        """Add badges based on recommendation scores."""
        # Recommended badge
        if self.is_recommended:
            match_badge = _get_match_badge(self.overall_score)
            self._create_badge(parent, match_badge)

        # Cloud/Local + Cost/Fit
        if self.is_cloud:
            self._create_badge(parent, FitBadge(f"☁ {self.provider.title()}", "#2d4a6d", "gray80"))
            cost_badge = _get_cost_badge(self.cost_score, True)
            if cost_badge:
                self._create_badge(parent, cost_badge)
        else:
            hw_badge = _get_hardware_fit_badge(self.hardware_fit_score)
            self._create_badge(parent, hw_badge)

    def _create_badge(self, parent, badge: FitBadge):
        """Create a single badge widget."""
        ctk.CTkLabel(
            parent,
            text=badge.text,
            font=("Arial", 10, "bold"),
            text_color=badge.text_color,
            fg_color=badge.fg_color,
            corner_radius=4,
            padx=6,
            pady=2
        ).pack(side="left", padx=(10, 0))

    def _add_cloud_stats(self, parent): pass # Deprecated
    def _add_local_stats(self, parent): pass # Deprecated

    def _build_expanded_view(self):
        """Build the collapsible expanded view."""
        self.expanded_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=0)

        # Separator
        sep = ctk.CTkFrame(self.expanded_frame, height=1, fg_color="gray30")
        sep.pack(fill="x")

        content = ctk.CTkFrame(self.expanded_frame, fg_color="transparent")
        content.pack(fill="x", padx=15, pady=12)

        # Score breakdown section
        self._add_score_breakdown(content)

        # Reasoning section
        if self.reasoning:
            ctk.CTkLabel(
                content,
                text="Why this model?",
                font=("Arial", 12, "bold"),
                anchor="w"
            ).pack(fill="x", pady=(10, 5))

            reasoning_text = "\n".join([f"• {r}" for r in self.reasoning[:3]])
            ctk.CTkLabel(
                content,
                text=reasoning_text,
                font=("Arial", 11),
                text_color="gray70",
                anchor="w",
                justify="left",
                wraplength=400
            ).pack(fill="x", pady=(0, 10))

        # Model-specific details
        if self.is_cloud:
            self._add_cloud_details(content)
        else:
            self._add_local_details(content)

    def _add_score_breakdown(self, parent):
        """Add score breakdown visualization."""
        ctk.CTkLabel(
            parent,
            text="Score Breakdown",
            font=("Arial", 12, "bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 5))

        scores_frame = ctk.CTkFrame(parent, fg_color="transparent")
        scores_frame.pack(fill="x", pady=(0, 5))

        if self.is_cloud:
            model_cloud = self.model
            scores = [
                ("Content Match", model_cloud.content_score),
                ("Cost Efficiency", model_cloud.cost_score),
                ("Provider Reliability", model_cloud.provider_score),
                ("Response Speed", model_cloud.latency_score),
            ]
        else:
            # Local models show 5 TOPSIS criteria scores for parity with cloud
            model_local = self.model
            scores = [
                ("Content Match", getattr(model_local, 'content_similarity_score', 0.5)),
                ("Hardware Fit", self.hardware_fit_score),
                ("Speed Estimate", getattr(model_local, 'speed_fit_score', 0.5)),
                ("Ecosystem", getattr(model_local, 'user_fit_score', 0.5)),
                ("Workflow Fit", getattr(model_local, 'approach_fit_score', 0.5)),
            ]

        for name, score in scores:
            row = ctk.CTkFrame(scores_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row,
                text=f"{name}:",
                font=("Arial", 10),
                text_color="gray60",
                width=120,
                anchor="w"
            ).pack(side="left")

            # Progress bar for score
            bar_frame = ctk.CTkFrame(row, fg_color="gray30", height=8, corner_radius=4)
            bar_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
            bar_frame.pack_propagate(False)

            fill_width = max(0.05, score)  # Min 5% visible
            fill_color = "#22c55e" if score >= 0.6 else "#eab308" if score >= 0.4 else "#ef4444"
            fill = ctk.CTkFrame(bar_frame, fg_color=fill_color, corner_radius=4)
            fill.place(relx=0, rely=0, relwidth=fill_width, relheight=1)

            ctk.CTkLabel(
                row,
                text=f"{score:.0%}",
                font=("Arial", 10),
                text_color="gray60",
                width=40
            ).pack(side="right")

    def _add_cloud_details(self, parent):
        """Add cloud-specific expanded details."""
        model_cloud = self.model

        # Setup type
        setup_type = "ComfyUI Partner Node" if model_cloud.setup_type == "partner_node" else "API Key Required"
        ctk.CTkLabel(
            parent,
            text=f"Setup: {setup_type}",
            font=("Arial", 11),
            text_color="gray60",
            anchor="w"
        ).pack(fill="x", pady=(5, 0))

        if model_cloud.storage_boost_applied:
            ctk.CTkLabel(
                parent,
                text="ℹ️ Recommended due to limited local storage",
                font=("Arial", 10),
                text_color="#60a5fa",
                anchor="w"
            ).pack(fill="x", pady=(5, 0))

    def _add_local_details(self, parent):
        """Add local model expanded details."""
        model_local = self.model
        reqs = getattr(model_local, 'requirements', {})

        # Requirements section - handle both MB and GB keys
        req_lines = []
        vram_min_mb = reqs.get('vram_min_mb', 0)
        vram_min_gb = reqs.get('vram_min_gb', vram_min_mb / 1024 if vram_min_mb else 0)
        vram_rec_mb = reqs.get('vram_recommended_mb', 0)
        vram_rec_gb = reqs.get('vram_recommended_gb', vram_rec_mb / 1024 if vram_rec_mb else 0)

        if vram_min_gb > 0:
            req_lines.append(f"• Minimum VRAM: {vram_min_gb:.0f} GB")
        if vram_rec_gb > 0:
            req_lines.append(f"• Recommended VRAM: {vram_rec_gb:.0f} GB")
        if reqs.get('size_gb'):
            req_lines.append(f"• Download size: {_format_size(reqs['size_gb'])}")

        if req_lines:
            ctk.CTkLabel(
                parent,
                text="Requirements",
                font=("Arial", 12, "bold"),
                anchor="w"
            ).pack(fill="x", pady=(5, 5))

            ctk.CTkLabel(
                parent,
                text="\n".join(req_lines),
                font=("Arial", 11),
                text_color="gray70",
                anchor="w",
                justify="left"
            ).pack(fill="x", pady=(0, 5))

        # Required nodes
        required_nodes = getattr(model_local, 'required_nodes', [])
        if required_nodes:
            ctk.CTkLabel(
                parent,
                text=f"Required extensions: {', '.join(required_nodes)}",
                font=("Arial", 11),
                text_color="gray60",
                anchor="w"
            ).pack(fill="x")

    def _toggle_expand(self):
        """Toggle between compact and expanded views."""
        self.expanded = not self.expanded

        if self.expanded:
            if self.expanded_frame is None:
                self._build_expanded_view()
            self.expanded_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=15, pady=(0, 12))
            self.expand_btn.configure(text="▲")
        else:
            if self.expanded_frame:
                self.expanded_frame.grid_forget()
            self.expand_btn.configure(text="▼")

    def _on_toggle(self):
        """Handle selection toggle."""
        if self.on_select:
            self.on_select(self.model_id, self.var_selected.get())

    def is_selected(self) -> bool:
        """Check if this model is selected."""
        return self.var_selected.get()

    def set_selected(self, selected: bool):
        """Programmatically set selection state."""
        self.var_selected.set(selected)

    def set_recommended(self, recommended: bool):
        """Update recommended state and rebuild visual."""
        self.is_recommended = recommended
        # Preserve expanded state and selection
        was_expanded = self.expanded
        was_selected = self.var_selected.get()

        # Rebuild UI with new recommended state
        self._build_ui()

        # Restore state
        self.var_selected.set(was_selected)
        if was_expanded:
            self._toggle_expand()
