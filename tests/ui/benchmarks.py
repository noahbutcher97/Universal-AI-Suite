import unittest
import time
import customtkinter as ctk
from typing import List
from unittest.mock import MagicMock

from src.ui.wizard.components.model_comparison import ModelComparisonView
from src.ui.wizard.components.model_card import ModelCard
from src.schemas.recommendation import ModelCandidate, RecommendationResults, ModelCapabilityScores
from src.utils.performance_monitor import get_performance_monitor

class BenchmarkSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = ctk.CTk()
            # cls.root.withdraw() # Headless benchmarks are faster, but we need update()
            # Keeping it visible or withdrawn doesn't matter much for logic, 
            # but update() is needed for 'after' callbacks.
        except Exception:
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        if cls.root:
            cls.root.destroy()

    def setUp(self):
        self.monitor = get_performance_monitor()
        self.monitor.clear()
        
        # Create base mock model
        self.mock_model = ModelCandidate(
            id="bench_model",
            display_name="Benchmark Model",
            tier="sdxl",
            capabilities=ModelCapabilityScores(),
            requirements={"size_gb": 5.0}
        )

    def pump_events(self, duration_ms: int = 100):
        """Simulate event loop processing."""
        if not self.root:
            return
        
        end_time = time.perf_counter() + (duration_ms / 1000)
        while time.perf_counter() < end_time:
            self.root.update()
            time.sleep(0.01)

    def test_scalability_render_time(self):
        """Benchmark: Render time scaling (10 vs 50 vs 100 models)."""
        if not self.root:
            self.skipTest("No display")

        counts = [10, 50, 100]
        
        for count in counts:
            label = f"render_scale_{count}"
            print(f"\n[BENCH] Running Scalability Test: {count} items")
            
            models = [self.mock_model] * count
            results = RecommendationResults(
                local_recommendations=models,
                cloud_recommendations=[],
                primary_pathway="local"
            )
            
            view = ModelComparisonView(self.root, results)
            
            # Start profiling
            with self.monitor.start_profile(label):
                with self.monitor.start_measure(label):
                    # Trigger render (async)
                    view.visible_count = count # Force render all
                    view._refresh_view()
                    
                    # Wait for render to complete (simulate)
                    # We need to wait enough time for the batched rendering to finish
                    # Batch size 2, delay 5ms -> ~2.5ms per item + overhead
                    wait_time = max(100, count * 5) 
                    self.pump_events(wait_time)
            
            stats = self.monitor.calculate_stats(label)
            print(f"  -> Duration: {stats.avg:.2f}ms")
            
            view.destroy()

    def test_rendering_throughput(self):
        """Benchmark: Throughput (Cards per second)."""
        if not self.root:
            self.skipTest("No display")
            
        count = 100
        label = "throughput_100"
        
        models = [self.mock_model] * count
        results = RecommendationResults(local_recommendations=models)
        view = ModelComparisonView(self.root, results)
        
        start_time = time.perf_counter()
        
        view.visible_count = count
        view._refresh_view()
        self.pump_events(count * 5) # Ensure completion
        
        total_time = time.perf_counter() - start_time
        throughput = count / total_time
        
        print(f"\n[BENCH] Throughput: {throughput:.2f} cards/sec")
        self.monitor.record_metric("throughput", throughput)
        
        view.destroy()

    def test_memory_growth(self):
        """Benchmark: Memory usage over repeated renders (Leak detection)."""
        if not self.root:
            self.skipTest("No display")
            
        iterations = 5
        models_per_iter = 50
        label = "memory_growth"
        
        models = [self.mock_model] * models_per_iter
        results = RecommendationResults(local_recommendations=models)
        
        initial_mem = self.monitor.process.memory_info().rss / (1024*1024)
        print(f"\n[BENCH] Initial Memory: {initial_mem:.2f} MB")
        
        view = ModelComparisonView(self.root, results)
        
        for i in range(iterations):
            # Render full set
            view.visible_count = models_per_iter
            view._refresh_view()
            self.pump_events(200)
            
            # Measure
            current_mem = self.monitor.process.memory_info().rss / (1024*1024)
            print(f"  -> Iter {i+1}: {current_mem:.2f} MB")
            
            # Clear (simulating tab switch)
            for widget in view.scroll_frame.winfo_children():
                widget.destroy()
            self.pump_events(50)
            
        final_mem = self.monitor.process.memory_info().rss / (1024*1024)
        growth = final_mem - initial_mem
        
        print(f"[BENCH] Total Memory Growth: {growth:.2f} MB")
        self.monitor.record_metric("memory_growth_total", growth)
        
        view.destroy()

if __name__ == '__main__':
    unittest.main()
