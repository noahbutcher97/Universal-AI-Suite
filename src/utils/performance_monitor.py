import time
import psutil
import os
import json
import functools
import logging
import cProfile
import pstats
import io
import statistics
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

# Configure logger
log = logging.getLogger(__name__)

@dataclass
class MetricStats:
    label: str
    count: int
    min: float
    max: float
    avg: float
    median: float
    p95: float
    p99: float
    std_dev: float

class PerformanceMonitor:
    """
    Singleton for tracking UI performance metrics.
    Measures execution time, CPU/Memory delta, and enforces thresholds.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PerformanceMonitor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.metrics: List[Dict[str, Any]] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = Path("logs/performance")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = True
        self.process = psutil.Process(os.getpid())

    def start_measure(self, label: str) -> 'PerformanceContext':
        """Start a measurement context."""
        return PerformanceContext(self, label)

    def start_profile(self, label: str) -> 'ProfileContext':
        """Start a cProfile context."""
        return ProfileContext(label, self.log_dir)

    def record_metric(self, label: str, duration_ms: float, memory_delta_mb: float = 0.0):
        """Record a single metric point."""
        metric = {
            "timestamp": datetime.now().isoformat(),
            "label": label,
            "duration_ms": duration_ms,
            "memory_delta_mb": memory_delta_mb,
            "cpu_percent": self.process.cpu_percent(),
            "memory_usage_mb": self.process.memory_info().rss / (1024 * 1024)
        }
        self.metrics.append(metric)
        log.debug(f"[PERF] {label}: {duration_ms:.2f}ms | Mem Delta: {memory_delta_mb:.2f}MB")

    def save_report(self):
        """Save aggregated metrics to disk."""
        if not self.metrics:
            return
            
        report = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "raw_metrics": self.metrics,
            "statistics": {
                label: asdict(self.calculate_stats(label))
                for label in set(m["label"] for m in self.metrics)
            }
        }
        
        filepath = self.log_dir / f"perf_report_{self.session_id}.json"
        try:
            with open(filepath, "w") as f:
                json.dump(report, f, indent=2)
            log.info(f"Performance report saved to {filepath}")
        except Exception as e:
            log.error(f"Failed to save performance report: {e}")

    def calculate_stats(self, label: str) -> MetricStats:
        """Calculate statistics for a specific metric label."""
        values = [m["duration_ms"] for m in self.metrics if m["label"] == label]
        if not values:
            return MetricStats(label, 0, 0, 0, 0, 0, 0, 0, 0)
            
        values.sort()
        count = len(values)
        
        return MetricStats(
            label=label,
            count=count,
            min=min(values),
            max=max(values),
            avg=statistics.mean(values),
            median=statistics.median(values),
            p95=values[int(count * 0.95)] if count > 1 else values[0],
            p99=values[int(count * 0.99)] if count > 1 else values[0],
            std_dev=statistics.stdev(values) if count > 1 else 0.0
        )

    def get_average_duration(self, label_prefix: str) -> float:
        """Get average duration for metrics starting with label_prefix."""
        relevant = [m["duration_ms"] for m in self.metrics if m["label"].startswith(label_prefix)]
        if not relevant:
            return 0.0
        return sum(relevant) / len(relevant)

    def clear(self):
        self.metrics = []

class PerformanceContext:
    """Context manager for measuring code blocks."""
    def __init__(self, monitor: PerformanceMonitor, label: str):
        self.monitor = monitor
        self.label = label
        self.start_time = 0.0
        self.start_mem = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        self.start_mem = self.monitor.process.memory_info().rss
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.perf_counter() - self.start_time) * 1000
        end_mem = self.monitor.process.memory_info().rss
        mem_delta = (end_mem - self.start_mem) / (1024 * 1024)
        self.monitor.record_metric(self.label, duration, mem_delta)

class ProfileContext:
    """Context manager for cProfile integration."""
    def __init__(self, label: str, output_dir: Path):
        self.label = label
        self.output_dir = output_dir
        self.profiler = cProfile.Profile()

    def __enter__(self):
        self.profiler.enable()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.profiler.disable()
        # Save stats
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"profile_{self.label}_{timestamp}.prof"
        filepath = self.output_dir / filename
        self.profiler.dump_stats(filepath)
        
        # Log summary
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20) # Top 20 lines
        log.info(f"[PROFILE] {self.label} summary:\n{s.getvalue()}")

def measure_time(label: Optional[str] = None):
    """Decorator for measuring function execution time."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            metric_label = label or func.__qualname__
            monitor = get_performance_monitor()
            with monitor.start_measure(metric_label):
                return func(*args, **kwargs)
        return wrapper
    return decorator

def get_performance_monitor() -> PerformanceMonitor:
    return PerformanceMonitor()
