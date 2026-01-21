"""
Model Comparison View Component for the Setup Wizard.

Per PLAN: Generation Focus MVP - This component displays model recommendations
with comparison lenses and Local/Cloud split view.

Fixed: Per-modality tabs instead of flat list across all modalities.
Fixed: Selection state preserved across lens/tab changes.
"""

import customtkinter as ctk
from typing import List, Dict, Callable, Optional, Set
from enum import Enum

from src.schemas.recommendation import (
    ModelCandidate,
    CloudRankedCandidate,
    RecommendationResults
)
from src.ui.wizard.components.model_card import ModelCard
from src.utils.performance_monitor import measure_time


class ComparisonLens(Enum):
    """Available comparison lenses for sorting models."""
    RECOMMENDED = "recommended"  # Overall match score
    QUALITY = "quality"          # Output quality score
    SPEED = "speed"              # Generation speed
    COST = "cost"                # Cost efficiency (cloud) / size (local)
    SIZE = "size"                # Download size


# Map modality IDs to display names and model categories
MODALITY_CONFIG = {
    "image": {
        "name": "Images",
        "icon": "🎨",
        "categories": ["image_generation", "image_editing", "image_upscaling"],
    },
    "video": {
        "name": "Video",
        "icon": "🎬",
        "categories": ["video_generation"],
    },
    "audio": {
        "name": "Audio",
        "icon": "🎵",
        "categories": ["audio_generation"],
    },
    "text": {
        "name": "Text/LLM",
        "icon": "📝",
        "categories": ["text_generation"],
    },
    "3d": {
        "name": "3D",
        "icon": "🎲",
        "categories": ["3d_generation"],
    },
}


class LensTabBar(ctk.CTkFrame):
    """Tab bar for switching between comparison lenses."""

    def __init__(
        self,
        master,
        on_lens_change: Callable[[ComparisonLens], None] = None
    ):
        super().__init__(master, fg_color="transparent")

        self.on_lens_change = on_lens_change
        self.current_lens = ComparisonLens.RECOMMENDED
        self.buttons: Dict[ComparisonLens, ctk.CTkButton] = {}

        lenses = [
            (ComparisonLens.RECOMMENDED, "★ Best Match"),
            (ComparisonLens.QUALITY, "Quality"),
            (ComparisonLens.SPEED, "Speed"),
            (ComparisonLens.COST, "Cost"),
            (ComparisonLens.SIZE, "Size"),
        ]

        for lens, label in lenses:
            btn = ctk.CTkButton(
                self,
                text=label,
                width=90,
                height=32,
                corner_radius=6,
                fg_color="#3b82f6" if lens == self.current_lens else "transparent",
                hover_color="#2563eb" if lens == self.current_lens else "gray25",
                text_color="white" if lens == self.current_lens else "gray60",
                command=lambda l=lens: self._on_tab_click(l)
            )
            btn.pack(side="left", padx=3)
            self.buttons[lens] = btn

    def _on_tab_click(self, lens: ComparisonLens):
        if lens == self.current_lens:
            return

        for l, btn in self.buttons.items():
            if l == lens:
                btn.configure(fg_color="#3b82f6", hover_color="#2563eb", text_color="white")
            else:
                btn.configure(fg_color="transparent", hover_color="gray25", text_color="gray60")

        self.current_lens = lens
        if self.on_lens_change:
            self.on_lens_change(lens)


class ModalityTabBar(ctk.CTkFrame):
    """Tab bar for switching between modality categories."""

    def __init__(
        self,
        master,
        modalities: List[str],
        on_modality_change: Callable[[str], None] = None
    ):
        super().__init__(master, fg_color="#2d2d2d", corner_radius=8)

        self.on_modality_change = on_modality_change
        self.modalities = modalities
        self.current_modality = modalities[0] if modalities else None
        self.buttons: Dict[str, ctk.CTkButton] = {}

        for modality in modalities:
            config = MODALITY_CONFIG.get(modality, {"name": modality, "icon": "📁"})
            label = f"{config['icon']} {config['name']}"

            btn = ctk.CTkButton(
                self,
                text=label,
                width=100,
                height=36,
                corner_radius=6,
                fg_color="#3b82f6" if modality == self.current_modality else "transparent",
                hover_color="#2563eb",
                command=lambda m=modality: self._on_tab_click(m)
            )
            btn.pack(side="left", padx=4, pady=4)
            self.buttons[modality] = btn

    def _on_tab_click(self, modality: str):
        if modality == self.current_modality:
            return

        for m, btn in self.buttons.items():
            btn.configure(fg_color="#3b82f6" if m == modality else "transparent")

        self.current_modality = modality
        if self.on_modality_change:
            self.on_modality_change(modality)


class PathwayToggle(ctk.CTkFrame):
    """Toggle between Local and Cloud recommendation views."""

    def __init__(
        self,
        master,
        cloud_willingness: str,
        local_count: int = 0,
        cloud_count: int = 0,
        on_pathway_change: Callable[[str], None] = None
    ):
        super().__init__(master, fg_color="transparent")

        self.on_pathway_change = on_pathway_change
        self.cloud_willingness = cloud_willingness

        self.show_local = cloud_willingness != "cloud_only"
        self.show_cloud = cloud_willingness != "local_only"

        if self.show_local and self.show_cloud:
            self.current_pathway = "cloud" if cloud_willingness in ["cloud_preferred", "cloud_only"] else "local"
        elif self.show_local:
            self.current_pathway = "local"
        else:
            self.current_pathway = "cloud"

        if self.show_local and self.show_cloud:
            container = ctk.CTkFrame(self, fg_color="#2d2d2d", corner_radius=8)
            container.pack()

            self.local_btn = ctk.CTkButton(
                container,
                text=f"💻 Local ({local_count})",
                width=120,
                height=36,
                corner_radius=6,
                fg_color="#3b82f6" if self.current_pathway == "local" else "transparent",
                hover_color="#2563eb",
                command=lambda: self._on_toggle("local")
            )
            self.local_btn.pack(side="left", padx=4, pady=4)

            self.cloud_btn = ctk.CTkButton(
                container,
                text=f"☁ Cloud ({cloud_count})",
                width=120,
                height=36,
                corner_radius=6,
                fg_color="#3b82f6" if self.current_pathway == "cloud" else "transparent",
                hover_color="#2563eb",
                command=lambda: self._on_toggle("cloud")
            )
            self.cloud_btn.pack(side="left", padx=4, pady=4)
        else:
            pathway_label = "Local Models" if self.show_local else "Cloud APIs"
            count = local_count if self.show_local else cloud_count
            ctk.CTkLabel(self, text=f"{pathway_label} ({count} available)", font=("Arial", 12), text_color="gray60").pack()

    def _on_toggle(self, pathway: str):
        if pathway == self.current_pathway:
            return

        self.current_pathway = pathway
        if hasattr(self, 'local_btn'):
            self.local_btn.configure(fg_color="#3b82f6" if pathway == "local" else "transparent")
        if hasattr(self, 'cloud_btn'):
            self.cloud_btn.configure(fg_color="#3b82f6" if pathway == "cloud" else "transparent")

        if self.on_pathway_change:
            self.on_pathway_change(pathway)

    def get_current_pathway(self) -> str:
        return self.current_pathway

    def update_counts(self, local_count: int, cloud_count: int):
        """Update the counts displayed on buttons."""
        if hasattr(self, 'local_btn'):
            self.local_btn.configure(text=f"💻 Local ({local_count})")
        if hasattr(self, 'cloud_btn'):
            self.cloud_btn.configure(text=f"☁ Cloud ({cloud_count})")


class ModelComparisonView(ctk.CTkFrame):
    """
    Main model comparison view component.

    Features:
    - Per-modality tabs (Images, Video, Audio, etc.)
    - Comparison lens tabs for sorting within each modality
    - Local/Cloud pathway toggle
    - Selection state preserved across all view changes
    """

    def __init__(
        self,
        master,
        results: RecommendationResults,
        selected_modalities: List[str] = None,
        cloud_willingness: str = "cloud_fallback",
        on_selection_change: Callable[[List[str], List[str]], None] = None
    ):
        super().__init__(master, fg_color="transparent")

        self.results = results
        self.selected_modalities = selected_modalities or ["image"]
        self.cloud_willingness = cloud_willingness
        self.on_selection_change = on_selection_change

        # Selection state - preserved across all view changes
        self.selected_local_ids: Set[str] = set()
        self.selected_cloud_ids: Set[str] = set()

        # Organize models by modality
        self.local_by_modality = self._organize_by_modality(results.local_recommendations, is_cloud=False)
        self.cloud_by_modality = self._organize_by_modality(results.cloud_recommendations, is_cloud=True)

        # Current view state
        self.current_lens = ComparisonLens.RECOMMENDED
        self.current_modality = self.selected_modalities[0] if self.selected_modalities else "image"
        self.current_pathway = results.primary_pathway

        # Card references for current view
        self.model_cards: Dict[str, ModelCard] = {}
        
        # Pagination state
        self.PAGE_SIZE = 10
        self.visible_count = self.PAGE_SIZE
        
        # Async Rendering State
        self.render_job = None
        self.models_to_render = []
        self.render_index = 0

        # Build UI
        self._build_header()
        self._build_content()

    def _organize_by_modality(
        self,
        models: List,
        is_cloud: bool
    ) -> Dict[str, List]:
        """Organize models into modality buckets based on their category."""
        by_modality = {m: [] for m in self.selected_modalities}

        for model in models:
            # Get model category
            if is_cloud:
                category = getattr(model, 'category', 'image_generation')
            else:
                # For local models, infer from tier or use default
                category = getattr(model, 'category', None)
                if not category:
                    # Fallback: check requirements or tier
                    tier = getattr(model, 'tier', '')
                    if 'video' in tier.lower():
                        category = 'video_generation'
                    elif 'audio' in tier.lower():
                        category = 'audio_generation'
                    elif 'text' in tier.lower() or 'llm' in tier.lower():
                        category = 'text_generation'
                    else:
                        category = 'image_generation'

            # Map category to modality
            for modality, config in MODALITY_CONFIG.items():
                if category in config.get('categories', []):
                    if modality in by_modality:
                        by_modality[modality].append(model)
                    break
            else:
                # Default to image if no match
                if 'image' in by_modality:
                    by_modality['image'].append(model)

        return by_modality

    def _build_header(self):
        """Build the header with controls."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(header, text="Select Models", font=("Arial", 20, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Choose the AI models you want to install. Switch tabs to compare models by category.",
            font=("Arial", 12),
            text_color="gray70"
        ).pack(anchor="w", pady=(5, 10))

        # Modality tabs (if multiple modalities selected)
        if len(self.selected_modalities) > 1:
            self.modality_tabs = ModalityTabBar(
                header,
                modalities=self.selected_modalities,
                on_modality_change=self._on_modality_change
            )
            self.modality_tabs.pack(fill="x", pady=(0, 10))

        # Controls row
        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.pack(fill="x")

        # Lens tabs
        self.lens_tabs = LensTabBar(controls, on_lens_change=self._on_lens_change)
        self.lens_tabs.pack(side="left")

        # Pathway toggle - counts will be updated per modality
        local_count = len(self.local_by_modality.get(self.current_modality, []))
        cloud_count = len(self.cloud_by_modality.get(self.current_modality, []))

        self.pathway_toggle = PathwayToggle(
            controls,
            cloud_willingness=self.cloud_willingness,
            local_count=local_count,
            cloud_count=cloud_count,
            on_pathway_change=self._on_pathway_change
        )
        self.pathway_toggle.pack(side="right")

    def _build_content(self):
        """Build the scrollable model cards area."""
        # Storage warning if applicable
        if self.results.storage_constrained and self.results.storage_warnings:
            warning_frame = ctk.CTkFrame(self, fg_color="#4a3f00", corner_radius=8)
            warning_frame.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(
                warning_frame,
                text="⚠️ Storage space is limited. Consider cloud options or smaller models.",
                font=("Arial", 11),
                text_color="#ffd700",
                wraplength=600
            ).pack(padx=15, pady=10)

        # Scrollable frame for cards
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", label_text="")
        self.scroll_frame.pack(fill="both", expand=True)
        
        # Internal state for rendering
        self.current_models = []
        self.rendered_count = 0
        self.show_more_btn = None

        # Initial render
        self._refresh_view()

    @measure_time("ModelComparisonView._refresh_view")
    def _refresh_view(self):
        """Full reset and render of the view (Tab Switch)."""
        # Cancel any pending render job
        if self.render_job:
            self.after_cancel(self.render_job)
            self.render_job = None
        
        # Reset State
        self.rendered_count = 0
        self.visible_count = self.PAGE_SIZE
        
        # 1. Calculate Full List
        current_pathway = self.pathway_toggle.get_current_pathway()
        if current_pathway == "local":
            raw_models = self.local_by_modality.get(self.current_modality, [])
            self.current_models = self._sort_local_models(raw_models)
        else:
            raw_models = self.cloud_by_modality.get(self.current_modality, [])
            self.current_models = self._sort_cloud_models(raw_models)

        # Update Counts
        local_count = len(self.local_by_modality.get(self.current_modality, []))
        cloud_count = len(self.cloud_by_modality.get(self.current_modality, []))
        self.pathway_toggle.update_counts(local_count, cloud_count)

        # 2. Clear UI
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.model_cards.clear()
        self.show_more_btn = None

        # 3. Handle Empty
        if not self.current_models:
            config = MODALITY_CONFIG.get(self.current_modality, {"name": self.current_modality})
            ctk.CTkLabel(
                self.scroll_frame,
                text=f"No {config['name'].lower()} models available for this configuration.",
                font=("Arial", 14),
                text_color="gray60"
            ).pack(pady=50)
            return

        # 4. Start Render
        self._schedule_batch_render()

    def _load_more(self):
        """Load next page (Append)."""
        if self.show_more_btn:
            self.show_more_btn.destroy()
            self.show_more_btn = None
            
        self.visible_count += self.PAGE_SIZE
        self._schedule_batch_render()

    def _schedule_batch_render(self):
        """Start the async render loop if items needed."""
        if self.render_job:
            self.after_cancel(self.render_job)
            
        self.render_job = self.after(1, self._render_next_batch)

    @measure_time("ModelComparisonView._render_next_batch")
    def _render_next_batch(self):
        """Render a small batch of cards (Incremental)."""
        BATCH_SIZE = 2 # Reduced to meet 30ms threshold (approx 10ms per card)
        
        current_pathway = self.pathway_toggle.get_current_pathway()
        is_cloud = (current_pathway != "local")
        selected_ids = self.selected_cloud_ids if is_cloud else self.selected_local_ids
        
        # Determine range to render
        target_count = min(self.visible_count, len(self.current_models))
        
        count = 0
        while self.rendered_count < target_count and count < BATCH_SIZE:
            model = self.current_models[self.rendered_count]
            is_recommended = (self.rendered_count == 0)
            
            model_id = model.model_id if is_cloud else model.id
            is_selected = model_id in selected_ids
            
            card = ModelCard(
                self.scroll_frame,
                model=model,
                is_cloud=is_cloud,
                is_recommended=is_recommended,
                on_select=self._on_model_select
            )

            if is_selected:
                card.set_selected(True)

            card.pack(fill="x", pady=6)
            self.model_cards[model_id] = card
            
            self.rendered_count += 1
            count += 1
            
        # Continue or Finish
        if self.rendered_count < target_count:
            self.render_job = self.after(5, self._render_next_batch)
        else:
            self.render_job = None
            self._render_footer()

    def _render_footer(self):
        """Render the 'Show More' button if needed."""
        if len(self.current_models) > self.rendered_count:
            remaining = len(self.current_models) - self.rendered_count
            self.show_more_btn = ctk.CTkButton(
                self.scroll_frame,
                text=f"Show More ({remaining})",
                fg_color="transparent",
                border_width=1,
                border_color="gray40",
                text_color="gray70",
                hover_color="gray20",
                command=self._load_more
            )
            self.show_more_btn.pack(pady=20)

    def _sort_local_models(self, models: List[ModelCandidate]) -> List[ModelCandidate]:
        """Sort local models based on current lens."""
        if not models:
            return []

        if self.current_lens == ComparisonLens.RECOMMENDED:
            return sorted(models, key=lambda m: m.composite_score, reverse=True)
        elif self.current_lens == ComparisonLens.QUALITY:
            return sorted(models, key=lambda m: getattr(m, 'user_fit_score', 0), reverse=True)
        elif self.current_lens == ComparisonLens.SPEED:
            return sorted(
                models,
                key=lambda m: getattr(m.capabilities, 'generation_speed', 0) if hasattr(m, 'capabilities') else 0,
                reverse=True
            )
        elif self.current_lens in [ComparisonLens.COST, ComparisonLens.SIZE]:
            return sorted(
                models,
                key=lambda m: m.requirements.get('size_gb', float('inf')) if hasattr(m, 'requirements') else float('inf')
            )
        return models

    def _sort_cloud_models(self, models: List[CloudRankedCandidate]) -> List[CloudRankedCandidate]:
        """Sort cloud models based on current lens."""
        if not models:
            return []

        if self.current_lens == ComparisonLens.RECOMMENDED:
            return sorted(models, key=lambda m: m.overall_score, reverse=True)
        elif self.current_lens == ComparisonLens.QUALITY:
            return sorted(models, key=lambda m: m.content_score, reverse=True)
        elif self.current_lens == ComparisonLens.SPEED:
            return sorted(models, key=lambda m: m.latency_score, reverse=True)
        elif self.current_lens == ComparisonLens.COST:
            return sorted(models, key=lambda m: m.cost_score, reverse=True)
        elif self.current_lens == ComparisonLens.SIZE:
            return sorted(models, key=lambda m: m.cost_score, reverse=True)
        return models

    def _on_modality_change(self, modality: str):
        """Handle modality tab change."""
        self.current_modality = modality
        self._refresh_view()

    def _on_lens_change(self, lens: ComparisonLens):
        """Handle lens tab change."""
        self.current_lens = lens
        self._refresh_view()

    def _on_pathway_change(self, pathway: str):
        """Handle pathway toggle."""
        self.current_pathway = pathway
        self._refresh_view()

    def _on_model_select(self, model_id: str, selected: bool):
        """Handle model selection change - update persistent state."""
        # Determine which set to update based on current view
        current_pathway = self.pathway_toggle.get_current_pathway()

        if current_pathway == "local":
            if selected:
                self.selected_local_ids.add(model_id)
            else:
                self.selected_local_ids.discard(model_id)
        else:
            if selected:
                self.selected_cloud_ids.add(model_id)
            else:
                self.selected_cloud_ids.discard(model_id)

        # Notify parent
        if self.on_selection_change:
            self.on_selection_change(list(self.selected_local_ids), list(self.selected_cloud_ids))

    def get_selected_models(self) -> Dict[str, List[str]]:
        """Get dictionary of selected model IDs by pathway."""
        return {
            "local": list(self.selected_local_ids),
            "cloud": list(self.selected_cloud_ids)
        }
