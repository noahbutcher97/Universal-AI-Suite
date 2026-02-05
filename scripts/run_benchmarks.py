"""
Comprehensive Performance Benchmarking for the Relational Recommendation Engine.
Establish baselines for:
1. SQL Query Throughput (Relational vs Linear)
2. Full Orchestration Latency (3-Layer Pipeline)
3. Manifest Generation Speed (Recursive dependency resolution)
"""

import time
import sys
from pathlib import Path
from typing import List

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.model_database import get_model_database
from src.services.recommendation_service import RecommendationService
from src.schemas.environment import EnvironmentReport
from src.schemas.recommendation import UserProfile, ContentPreferences
from src.config.manager import config_manager

def benchmark_sql_vs_linear():
    db = get_model_database()
    print("\n[1/3] Benchmarking Database Throughput...")
    
    # SQL Lookup
    start = time.perf_counter()
    for _ in range(100):
        _ = db.get_compatible_models("windows_nvidia", 12000, ["image_generation"])
    sql_duration = (time.perf_counter() - start) / 100 * 1000
    
    print(f" - Average Relational Query (Indexed SQL): {sql_duration:.2f}ms")
    
    # Full Model Load (Simulating legacy linear scan cost)
    start = time.perf_counter()
    for _ in range(10):
        _ = db.get_all_models()
    linear_duration = (time.perf_counter() - start) / 10 * 1000
    print(f" - Average Full Table Load (Comparison): {linear_duration:.2f}ms")

def benchmark_orchestration_latency():
    service = RecommendationService(config_manager.get_resources())
    print("\n[2/3] Benchmarking Full 3-Layer Orchestration...")
    
    env = EnvironmentReport(
        gpu_vendor="nvidia",
        gpu_name="RTX 4090",
        vram_gb=24.0,
        ram_gb=64.0,
        os_name="Windows",
        os_version="10.0.19045",
        arch="x86_64",
        disk_free_gb=1000,
        form_factor="desktop"
    )
    
    profile = UserProfile(
        primary_use_cases=["txt2img"],
        content_preferences={"txt2img": ContentPreferences(generation_speed=5)}
    )
    
    # Warm-up
    service.generate_parallel_recommendations(profile, env, skip_snapshot=True)
    
    start = time.perf_counter()
    iterations = 50
    for _ in range(iterations):
        _ = service.generate_parallel_recommendations(profile, env, skip_snapshot=True)
    
    duration = (time.perf_counter() - start) / iterations * 1000
    print(f" - Full TOPSIS Pipeline (338 models): {duration:.2f}ms")
    
    # Goal: < 100ms for instant UI feedback
    if duration < 100:
        print("   ✅ PERFORMANCE TARGET MET")
    else:
        print("   ⚠️ PERFORMANCE WARNING: Latency above 100ms")

def benchmark_manifest_generation():
    service = RecommendationService(config_manager.get_resources())
    print("\n[3/3] Benchmarking Manifest Generation...")
    
    env = EnvironmentReport(
        gpu_vendor="nvidia", 
        gpu_name="RTX 4090",
        vram_gb=24.0, 
        ram_gb=64.0, 
        os_name="Windows", 
        os_version="10.0.19045",
        arch="x86_64",
        disk_free_gb=1000
    )
    profile = UserProfile(primary_use_cases=["txt2img"])
    results = service.generate_parallel_recommendations(profile, env)
    
    # Pick top 5 models
    recommendations = results.local_recommendations[:5]
    
    start = time.perf_counter()
    iterations = 50
    for _ in range(iterations):
        _ = service.generate_full_manifest(profile, recommendations)
    
    duration = (time.perf_counter() - start) / iterations * 1000
    print(f" - Recursive Dependency Resolution (Top 5): {duration:.2f}ms")

if __name__ == "__main__":
    print("AI Universal Suite - Relational Engine Benchmarks")
    print("=" * 50)
    try:
        benchmark_sql_vs_linear()
        benchmark_orchestration_latency()
        benchmark_manifest_generation()
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
    print("\n" + "=" * 50)