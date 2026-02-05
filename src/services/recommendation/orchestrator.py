"""
Recommendation Orchestrator Facade.
Part of Task PAT-01: Extract Recommendation Orchestrator Facade.

Coordinates the 3-layer recommendation engine:
1. Layer 1: Constraint Satisfaction (CSP)
2. Layer 2: Content-Based Filtering
3. Layer 3: TOPSIS Multi-Criteria Ranking
"""

from typing import List, Dict, Any, Optional, Tuple
from src.schemas.hardware import HardwareProfile
from src.schemas.recommendation import (
    UserProfile, 
    UseCaseDefinition, 
    ModelCandidate,
    RecommendationResults
)
from src.services.model_database import ModelDatabase, ModelEntry, ModelVariant
from src.services.recommendation.constraint_layer import (
    ConstraintSatisfactionLayer, 
    PassingCandidate, 
    RejectedCandidate
)
from src.services.recommendation.content_layer import ContentBasedLayer, ScoredCandidate
from src.services.recommendation.topsis_layer import TOPSISLayer, RankedCandidate
from src.utils.logger import log

class RecommendationOrchestrator:
    """
    Facade class that coordinates the multi-layered recommendation process.
    Provides a clean API for the UI and other services.
    """
    
    def __init__(self, model_db: Optional[ModelDatabase] = None):
        """
        Initialize the orchestrator with its component layers.
        """
        from src.services.model_database import get_model_database
        self.model_db = model_db or get_model_database()
        
        self.constraint_layer = ConstraintSatisfactionLayer(self.model_db)
        self.content_layer = ContentBasedLayer()
        self.topsis_layer = TOPSISLayer()

    def recommend_models(
        self,
        hardware: HardwareProfile,
        user_profile: UserProfile,
        use_case: str,
        categories: Optional[List[str]] = None
    ) -> Tuple[List[RankedCandidate], List[RejectedCandidate]]:
        """
        Execute the full 3-layer recommendation pipeline.
        
        Returns:
            Tuple of (top_ranked_candidates, all_rejected_candidates)
        """
        log.info(f"Orchestrating recommendations for use_case: {use_case}")
        
        # 1. Layer 1: Filter by Hard Constraints (CSP)
        passing, rejected = self.constraint_layer.filter(
            hardware=hardware,
            categories=categories
        )
        log.debug(f"Layer 1: {len(passing)} passed, {len(rejected)} rejected.")
        
        if not passing:
            return [], rejected

        # 2. Layer 2: Score by Content Similarity
        # Note: In a full implementation, we'd use use_case_templates
        scored = self.content_layer.score(
            candidates=passing,
            user_profile=user_profile,
            use_case=use_case
        )
        log.debug(f"Layer 2: Scored {len(scored)} candidates.")

        # 3. Layer 3: Final TOPSIS Ranking
        ranked = self.topsis_layer.rank(
            candidates=scored,
            hardware=hardware,
            user_profile=user_profile
        )
        log.info(f"Orchestration complete. Top candidate: {ranked[0].scored_candidate.passing_candidate.model.name if ranked else 'None'}")
        
        return ranked, rejected

    def get_use_case_definition(self, use_case_id: str) -> Optional[UseCaseDefinition]:
        """
        Helper to retrieve formal UseCaseDefinition for a use case key.
        """
        # This will eventually pull from a use_cases.yaml or templates registry
        return None
