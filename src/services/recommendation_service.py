import json
from src.services.system_service import SystemService
from src.config.manager import config_manager

class RecommendationService:
    @staticmethod
    def recommend(user_profile: dict) -> dict:
        """
        Generates a recommendation based on user profile and system hardware.
        """
        _, vram = SystemService.get_gpu_info()
        res = config_manager.get_resources().get("comfy", {})
        reasoning = []
        warnings = []

        # 1. Select Base Model Tier
        model_tier = "sd15"
        for tier, reqs in res.get("model_tiers", {}).items():
            if vram >= reqs["min_vram"]:
                model_tier = tier
                reasoning.append(f"Selected {tier} tier based on {vram}GB VRAM (requires {reqs['min_vram']}GB).")
                break

        # 2. Select Specific Model based on Style
        style = user_profile.get("style", "General").lower()
        models_by_style = res.get("models", {}).get(style, res.get("models", {}).get("general"))
        base_model = models_by_style.get(model_tier) if models_by_style else None
        if base_model:
            reasoning.append(f"Selected model '{base_model['name']}' for style '{style}'.")

        # 3. Select Custom Nodes (Features)
        selected_features = []
        feature_map = {
            "Video": "animatediff",
            "Mixed": "animatediff",
            "Editing": "controlnet",
            "Consistency": "ipadapter"
        }

        media_type = user_profile.get("media", "Image")
        if media_type in feature_map:
            feat_key = feature_map[media_type]
            selected_features.append(feat_key)
            reasoning.append(f"Added feature '{feat_key}' for media type '{media_type}'.")

        if user_profile.get("consistency"):
            selected_features.append("ipadapter")
            reasoning.append("Added 'ipadapter' for consistency.")

        if user_profile.get("editing"):
            selected_features.append("controlnet")
            reasoning.append("Added 'controlnet' for editing capabilities.")

        # Deduplicate features
        selected_features = list(set(selected_features))

        return {
            "recommendation_id": "auto_gen",
            "score": 1.0,
            "setup_profile": {
                "base_model": base_model,
                "quantization": "none",
                "custom_nodes": selected_features,
                "workflow_template": "default.json"
            },
            "reasoning": reasoning,
            "warnings": warnings
        }
