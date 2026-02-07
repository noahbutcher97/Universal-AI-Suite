"""
Master Regression Suite Runner.
Executes tests in stages to prevent timeouts and ensure stability.
Generates a consolidated coverage report.
"""

import sys
import subprocess
import os
from pathlib import Path

# Config
# Use venv python if available, else system python
venv_python = Path(__file__).parent.parent / ".dashboard_env" / "venv" / "Scripts" / "python.exe"
if venv_python.exists():
    PYTHON = str(venv_python)
else:
    PYTHON = sys.executable

BASE_CMD = [PYTHON, "-m", "pytest"]
COV_CMD = ["--cov=src", "--cov-report=term-missing", "--cov-append"]

def run_suite(name, path, timeout=300):
    print(f"\n[Regression] Running {name} Suite...")
    print(f"Python: {PYTHON}")
    cmd = BASE_CMD + COV_CMD + path.split()
    print(f"Command: {cmd}")
    try:
        # Run pytest
        result = subprocess.run(cmd, check=True, timeout=timeout)
        print(f"✅ {name} Suite Passed")
        return True
    except subprocess.TimeoutExpired:
        print(f"❌ {name} Suite Timed Out!")
        return False
    except subprocess.CalledProcessError:
        print(f"❌ {name} Suite Failed!")
        return False

def main():
    print("🚀 AI Universal Suite - Automated Regression Testing")
    print("Target: 95% Coverage | Scope: Functional, Performance, Security")
    print("=" * 60)

    # Clean previous coverage
    if os.path.exists(".coverage"):
        os.remove(".coverage")

    # 1. Services (Unit)
    if not run_suite("Services (Unit)", "tests/services"):
        sys.exit(1)

    # 2. Integration
    if not run_suite("Integration", "tests/integration"):
        sys.exit(1)

    # 3. Config & Schemas
    if not run_suite("Config & Schemas", "tests/config tests/schemas"):
        sys.exit(1)

    # 4. Installation & E2E
    if not run_suite("Installation & E2E", "tests/installation tests/e2e"):
        sys.exit(1)

    # 5. UI & Performance
    if not run_suite("UI & Performance", "tests/ui tests/performance"):
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ All Test Suites Passed!")
    
    # Generate HTML Report
    print("Generating Coverage Report...")
    subprocess.run([PYTHON, "-m", "coverage", "html", "-d", "logs/coverage_report"])
    print(f"Report available at: {os.path.abspath('logs/coverage_report/index.html')}")

if __name__ == "__main__":
    main()
