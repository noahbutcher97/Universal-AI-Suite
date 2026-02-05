"""
Unit tests for PAT-01: Recommendation Orchestrator Facade.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.services.recommendation.orchestrator import RecommendationOrchestrator
from src.schemas.hardware import HardwareProfile
from src.schemas.model import ModelEntry
from src.schemas.recommendation import (
    UserProfile, 
    PassingCandidate, 
    RejectedCandidate,
    ScoredCandidate,
    RankedCandidate
)

class TestRecommendationOrchestrator:
    """Tests for coordination logic in the Orchestrator Facade."""

    @pytest.fixture
    def mock_layers(self):
        """Provides an orchestrator with all layers mocked."""
        with patch("src.services.model_database.get_model_database") as mock_db:
            orchestrator = RecommendationOrchestrator(model_db=mock_db)
            orchestrator.constraint_layer = MagicMock()
            orchestrator.content_layer = MagicMock()
            orchestrator.topsis_layer = MagicMock()
            return orchestrator

    def test_orchestration_flow_success(self, mock_layers):
        """Verify the full 3-layer pipeline executes in order."""
        # 1. Setup Mocks
        passing_item = MagicMock(spec=PassingCandidate)
        mock_layers.constraint_layer.filter.return_value = ([passing_item], [])
        
        scored_item = MagicMock(spec=ScoredCandidate)
        mock_layers.content_layer.score.return_value = [scored_item]
        
        ranked_item = MagicMock(spec=RankedCandidate)
        # Setup nested mocks for log string access
        ranked_item.scored_candidate = MagicMock(spec=ScoredCandidate)
        ranked_item.scored_candidate.passing_candidate = MagicMock(spec=PassingCandidate)
        ranked_item.scored_candidate.passing_candidate.model = MagicMock(spec=ModelEntry)
        ranked_item.scored_candidate.passing_candidate.model.name = "Test Model"
        
        mock_layers.topsis_layer.rank.return_value = [ranked_item]
        
        # 2. Execute
        hardware = MagicMock(spec=HardwareProfile)
        profile = MagicMock(spec=UserProfile)
        ranked, rejected = mock_layers.recommend_models(hardware, profile, "test_uc")
        
        # 3. Verify Coordination
        assert len(ranked) == 1
        assert ranked[0] == ranked_item
        
        # Ensure Layer 1 was called
        mock_layers.constraint_layer.filter.assert_called_once()
        
        # Ensure Layer 2 was called with output of Layer 1
        mock_layers.content_layer.score.assert_called_once_with(
            candidates=[passing_item], 
            user_profile=profile, 
            use_case="test_uc"
        )
        
        # Ensure Layer 3 was called with output of Layer 2
        mock_layers.topsis_layer.rank.assert_called_once_with(
            candidates=[scored_item], 
            hardware=hardware, 
            user_profile=profile
        )

    def test_early_exit_no_passing_candidates(self, mock_layers):
        """Verify orchestrator exits early if Layer 1 rejects everything."""
        # Setup Layer 1 to return empty passing list
        rejection = MagicMock(spec=RejectedCandidate)
        mock_layers.constraint_layer.filter.return_value = ([], [rejection])
        
        ranked, rejected = mock_layers.recommend_models(MagicMock(), MagicMock(), "test")
        
        assert len(ranked) == 0
        assert len(rejected) == 1
        
        # Layer 2 and 3 should NOT be called
        mock_layers.content_layer.score.assert_not_called()
        mock_layers.topsis_layer.rank.assert_not_called()
