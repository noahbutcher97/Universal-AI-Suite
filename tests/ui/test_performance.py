import unittest
import time
from unittest.mock import MagicMock, patch
import customtkinter as ctk

from src.ui.wizard.components.model_comparison import ModelComparisonView
from src.ui.wizard.components.model_card import ModelCard
from src.schemas.recommendation import RankedCandidate, RecommendationResults
from src.utils.performance_monitor import get_performance_monitor

# Performance Thresholds (ms)
THRESHOLDS = {
    "ModelCard.__init__": 10.0,  # Should be very fast with flattened layout
    "ModelComparisonView._render_next_batch": 30.0,  # Strict threshold for UI responsiveness
}

class TestUIPerformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize CTk (headless if possible, but for unit tests we mock parent)
        # We need a root window for widgets to attach to, even if not shown
        try:
            cls.root = ctk.CTk()
            cls.root.withdraw() # Hide it
        except Exception:
            # If no display, some tests might fail or need mocking.
            # Assuming dev env has display or Xvfb.
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        if cls.root:
            cls.root.destroy()

    def setUp(self):
        self.monitor = get_performance_monitor()
        self.monitor.clear()
        
        # Mock Data
        self.mock_model = MagicMock(spec=RankedCandidate)
        self.mock_model.id = "test_model"
        self.mock_model.display_name = "Test Model"
        self.mock_model.tier = "sdxl"
        self.mock_model.composite_score = 0.9
        self.mock_model.hardware_fit_score = 0.8
        self.mock_model.content_similarity_score = 0.9
        self.mock_model.speed_fit_score = 0.7
        self.mock_model.user_fit_score = 0.8
        self.mock_model.approach_fit_score = 0.9
        self.mock_model.reasoning = ["Excellent fit"]
        self.mock_model.requirements = {"size_gb": 5.0}
        self.mock_model.required_nodes = []
        self.mock_results = RecommendationResults(
            local_recommendations=[self.mock_model] * 20,
            cloud_recommendations=[],
            primary_pathway="local"
        )

    def test_model_card_init_performance(self):
        """Test ModelCard initialization speed."""
        if not self.root:
            self.skipTest("No display available for UI tests")

        # Measure creation of 10 cards
        start = time.perf_counter()
        for _ in range(10):
            card = ModelCard(self.root, self.mock_model)
            card.destroy() # Cleanup
        duration_ms = (time.perf_counter() - start) * 1000 / 10
        
        # Verify via Monitor
        avg_monitor = self.monitor.get_average_duration("ModelCard.__init__")
        
        print(f"\n[PERF] ModelCard init avg: {avg_monitor:.2f}ms")
        self.assertLess(avg_monitor, THRESHOLDS["ModelCard.__init__"])

    def test_batch_render_performance(self):
        """Test render batch processing speed."""
        if not self.root:
            self.skipTest("No display available for UI tests")

        # Setup View
        view = ModelComparisonView(self.root, self.mock_results)
        
        # Force a render batch
        view.models_to_render = [self.mock_model] * 10
        view.render_index = 0
        
        # Execute batch synchronously for test
        view._render_next_batch()
        
        # Verify via Monitor
        avg_monitor = self.monitor.get_average_duration("ModelComparisonView._render_next_batch")
        
        print(f"\n[PERF] Batch render avg: {avg_monitor:.2f}ms")
        self.assertLess(avg_monitor, THRESHOLDS["ModelComparisonView._render_next_batch"])
        
        # Cleanup
        view.destroy()

    def test_edge_cases(self):
        """Test performance with 0 and 1 items."""
        if not self.root:
            self.skipTest("No display")
            
        # Empty
        view = ModelComparisonView(self.root, RecommendationResults())
        with self.monitor.start_measure("render_empty"):
            view._refresh_view()
        view.destroy()
        
        # Single
        single_res = RecommendationResults(local_recommendations=[self.mock_model])
        view = ModelComparisonView(self.root, single_res)
        with self.monitor.start_measure("render_single"):
            view._refresh_view()
            # Simulate slight wait for async batch
            time.sleep(0.01) 
        view.destroy()
        
        empty_time = self.monitor.get_average_duration("render_empty")
        single_time = self.monitor.get_average_duration("render_single")
        
        print(f"\n[PERF] Empty Render: {empty_time:.2f}ms")
        print(f"[PERF] Single Render: {single_time:.2f}ms")
        
        self.assertLess(empty_time, 10.0)
        self.assertLess(single_time, 20.0)

    def test_memory_threshold(self):
        """Ensure memory usage stays within reasonable limits during operations."""
        # Baseline
        mem_start = self.monitor.process.memory_info().rss / (1024*1024)
        
        # Create heavy view
        view = ModelComparisonView(self.root, RecommendationResults(
            local_recommendations=[self.mock_model] * 50
        ))
        
        mem_peak = self.monitor.process.memory_info().rss / (1024*1024)
        delta = mem_peak - mem_start
        
        print(f"\n[PERF] Memory Delta for 50 items: {delta:.2f} MB")
        
        # Threshold: 50 items shouldn't take more than 50MB (1MB per item overhead is generous)
        self.assertLess(delta, 50.0)
        
        view.destroy()

if __name__ == '__main__':
    unittest.main()
