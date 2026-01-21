import unittest
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_benchmarks():
    """Run all performance tests and benchmarks."""
    print("="*60)
    print("🚀 AI Universal Suite - Performance Benchmark Suite")
    print("="*60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Load Tests
    suite.addTests(loader.loadTestsFromName("tests.ui.test_performance"))
    suite.addTests(loader.loadTestsFromName("tests.ui.benchmarks"))
    
    # Run
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Report
    print("\n" + "="*60)
    if result.wasSuccessful():
        print("✅ ALL BENCHMARKS PASSED")
        print("Check logs/performance/ for detailed metrics and profiling data.")
    else:
        print("❌ SOME BENCHMARKS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    run_benchmarks()
