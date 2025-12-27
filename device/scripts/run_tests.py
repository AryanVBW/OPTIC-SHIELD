#!/usr/bin/env python3
"""
OPTIC-SHIELD Test Runner

Runs comprehensive tests and generates a "Tested OK" report.

Usage:
    python scripts/run_tests.py
    python scripts/run_tests.py --json          # JSON output
    python scripts/run_tests.py --report FILE   # Save report to file
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class TestResult:
    """Result of a single test."""

    name: str
    passed: bool
    duration_ms: float
    message: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "duration_ms": round(self.duration_ms, 2),
            "message": self.message,
            "error": self.error,
        }


@dataclass
class TestReport:
    """Complete test report."""

    timestamp: str
    install_dir: str
    platform: Dict[str, Any]
    tests: List[TestResult] = field(default_factory=list)
    total_duration_ms: float = 0

    @property
    def passed_count(self) -> int:
        return sum(1 for t in self.tests if t.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for t in self.tests if not t.passed)

    @property
    def all_passed(self) -> bool:
        return self.failed_count == 0

    def add_result(self, result: TestResult):
        self.tests.append(result)
        self.total_duration_ms += result.duration_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "install_dir": self.install_dir,
            "platform": self.platform,
            "summary": {
                "total": len(self.tests),
                "passed": self.passed_count,
                "failed": self.failed_count,
                "all_passed": self.all_passed,
                "total_duration_ms": round(self.total_duration_ms, 2),
            },
            "tests": [t.to_dict() for t in self.tests],
        }


class TestRunner:
    """Runs all OPTIC-SHIELD tests."""

    def __init__(self, install_dir: Optional[Path] = None):
        self.install_dir = install_dir or Path(__file__).parent.parent
        self.report: Optional[TestReport] = None

    def run_test(self, name: str, test_func) -> TestResult:
        """Run a single test function."""
        start_time = time.perf_counter()

        try:
            result, message = test_func()
            duration = (time.perf_counter() - start_time) * 1000

            return TestResult(
                name=name, passed=result, duration_ms=duration, message=message
            )
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000
            return TestResult(
                name=name,
                passed=False,
                duration_ms=duration,
                message="Test failed with exception",
                error=str(e),
            )

    def run_all_tests(self) -> TestReport:
        """Run all tests."""
        # Get platform info
        try:
            from src.utils.platform_detector import get_detector

            detector = get_detector(self.install_dir)
            platform_info = detector.get_full_report()
        except Exception as e:
            platform_info = {"error": str(e)}

        self.report = TestReport(
            timestamp=datetime.now().isoformat(),
            install_dir=str(self.install_dir),
            platform=platform_info,
        )

        # Define tests
        tests = [
            ("Import Core Modules", self._test_import_core),
            ("Import Platform Detector", self._test_import_platform),
            ("Configuration Loading", self._test_config_loading),
            ("Camera Manager Init", self._test_camera_init),
            ("Detector Init", self._test_detector_init),
            ("Database Connection", self._test_database),
            ("Image Storage", self._test_image_storage),
            ("Logging Setup", self._test_logging),
            ("Detection Pipeline", self._test_detection_pipeline),
            ("System Monitor", self._test_system_monitor),
        ]

        print("\n🧪 Running OPTIC-SHIELD Tests...\n")

        for name, test_func in tests:
            result = self.run_test(name, test_func)
            self.report.add_result(result)

            # Print progress
            icon = "✓" if result.passed else "✗"
            color = "\033[92m" if result.passed else "\033[91m"
            nc = "\033[0m"
            print(
                f"  {color}{icon}{nc} {name}: {result.message} ({result.duration_ms:.1f}ms)"
            )

        return self.report

    # =========================================================================
    # Test Functions
    # =========================================================================

    def _test_import_core(self):
        """Test importing core modules."""
        import numpy
        import yaml
        from PIL import Image

        return True, f"numpy={numpy.__version__}"

    def _test_import_platform(self):
        """Test platform detector import."""
        from src.utils.platform_detector import (
            get_os_type,
            get_user_info,
            is_raspberry_pi,
        )

        os_type = get_os_type()
        return True, f"OS={os_type.value}"

    def _test_config_loading(self):
        """Test configuration loading."""
        from src.core.config import Config

        Config.reset_instance()
        config = Config.get_instance(self.install_dir / "config")

        return True, f"Environment={config.environment}"

    def _test_camera_init(self):
        """Test camera manager initialization."""
        from src.core.camera import CameraManager, CameraType

        camera = CameraManager(width=320, height=240)
        # Don't actually initialize camera, just test the class

        return True, "CameraManager class OK"

    def _test_detector_init(self):
        """Test detector initialization."""
        from src.core.detector import WildlifeDetector

        detector = WildlifeDetector(
            model_path="models/yolo11n_ncnn_model", fallback_path="models/yolo11n.pt"
        )

        return True, "WildlifeDetector class OK"

    def _test_database(self):
        """Test database operations."""
        import sqlite3

        db_path = self.install_dir / "data" / "test.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Create test table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS test (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """
        )

        # Insert and query
        cursor.execute("INSERT INTO test (value) VALUES (?)", ("test_value",))
        cursor.execute("SELECT value FROM test WHERE id = ?", (cursor.lastrowid,))
        result = cursor.fetchone()

        conn.close()
        db_path.unlink()  # Cleanup

        if result and result[0] == "test_value":
            return True, "SQLite CRUD OK"
        return False, "Data mismatch"

    def _test_image_storage(self):
        """Test image storage operations."""
        from PIL import Image
        import io

        # Create test image
        img = Image.new("RGB", (100, 100), color="red")

        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)

        size = len(buffer.getvalue())
        return True, f"JPEG encoding OK ({size} bytes)"

    def _test_logging(self):
        """Test logging setup."""
        from src.utils.logging_setup import setup_logging
        from src.core.config import Config

        config = Config.get_instance()
        # Just test the import, don't actually setup logging

        return True, "Logging module OK"

    def _test_detection_pipeline(self):
        """Test the detection pipeline."""
        import numpy as np
        from src.core.detector import Detection

        # Create a mock detection
        detection = Detection(
            class_id=15,
            class_name="cat",
            confidence=0.95,
            bbox=(10, 20, 100, 150),
            timestamp=time.time(),
        )

        data = detection.to_dict()

        if all(k in data for k in ["class_id", "class_name", "confidence", "bbox"]):
            return True, "Detection dataclass OK"
        return False, "Missing detection fields"

    def _test_system_monitor(self):
        """Test system monitor."""
        from src.utils.system_monitor import SystemMonitor

        monitor = SystemMonitor(check_interval=1)
        stats = monitor.get_stats()

        return True, f"CPU={stats.cpu_percent}%"


def print_report(report: TestReport):
    """Print formatted test report."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    NC = "\033[0m"

    print()
    print(f"{BLUE}╔══════════════════════════════════════════════════════════════╗{NC}")
    print(
        f"{BLUE}║{NC}                  OPTIC-SHIELD TEST REPORT                    {BLUE}║{NC}"
    )
    print(f"{BLUE}╠══════════════════════════════════════════════════════════════╣{NC}")

    # Summary
    print(f"{BLUE}║{NC}  Tests Run:    {len(report.tests)}")
    print(f"{BLUE}║{NC}  {GREEN}Passed:{NC}       {report.passed_count}")
    print(f"{BLUE}║{NC}  {RED}Failed:{NC}       {report.failed_count}")
    print(f"{BLUE}║{NC}  Duration:     {report.total_duration_ms:.1f}ms")

    print(f"{BLUE}╠══════════════════════════════════════════════════════════════╣{NC}")

    if report.all_passed:
        print(
            f"{BLUE}║{NC}                                                              {BLUE}║{NC}"
        )
        print(
            f"{BLUE}║{NC}   {GREEN}✅ TESTED OK - All tests passed!{NC}                          {BLUE}║{NC}"
        )
        print(
            f"{BLUE}║{NC}   {GREEN}   Ready to use OPTIC-SHIELD{NC}                              {BLUE}║{NC}"
        )
        print(
            f"{BLUE}║{NC}                                                              {BLUE}║{NC}"
        )
    else:
        print(
            f"{BLUE}║{NC}                                                              {BLUE}║{NC}"
        )
        print(
            f"{BLUE}║{NC}   {RED}❌ TESTS FAILED{NC}                                            {BLUE}║{NC}"
        )
        print(
            f"{BLUE}║{NC}                                                              {BLUE}║{NC}"
        )

        # Show failed tests
        for test in report.tests:
            if not test.passed:
                print(
                    f"{BLUE}║{NC}   {RED}✗{NC} {test.name}: {test.error or test.message}"
                )

    print(f"{BLUE}╚══════════════════════════════════════════════════════════════╝{NC}")
    print()


def save_report(report: TestReport, filepath: Path):
    """Save report to file."""
    with open(filepath, "w") as f:
        json.dump(report.to_dict(), f, indent=2)
    print(f"Report saved to: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Run OPTIC-SHIELD tests")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--report", type=str, default=None, help="Save report to file")
    parser.add_argument("--dir", type=str, default=None, help="Installation directory")

    args = parser.parse_args()

    install_dir = Path(args.dir) if args.dir else None
    runner = TestRunner(install_dir)
    report = runner.run_all_tests()

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_report(report)

    if args.report:
        save_report(report, Path(args.report))

    # Exit with appropriate code
    sys.exit(0 if report.all_passed else 1)


if __name__ == "__main__":
    main()
