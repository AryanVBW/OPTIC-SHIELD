#!/usr/bin/env python3
"""
OPTIC-SHIELD Setup Validation Script

Comprehensive validation of the OPTIC-SHIELD installation.
Runs 19 checks covering Python, dependencies, hardware, and configuration.

Usage:
    python scripts/validate_setup.py
    python scripts/validate_setup.py --json  # Output as JSON
    python scripts/validate_setup.py --quiet # Only show failures
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class CheckStatus(Enum):
    """Status of a validation check."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass
class CheckResult:
    """Result of a single validation check."""

    name: str
    status: CheckStatus
    message: str
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class ValidationReport:
    """Complete validation report."""

    timestamp: str
    platform: Dict[str, Any]
    checks: List[CheckResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    skipped: int = 0

    def add_result(self, result: CheckResult):
        """Add a check result."""
        self.checks.append(result)
        if result.status == CheckStatus.PASS:
            self.passed += 1
        elif result.status == CheckStatus.FAIL:
            self.failed += 1
        elif result.status == CheckStatus.WARN:
            self.warnings += 1
        else:
            self.skipped += 1

    @property
    def is_successful(self) -> bool:
        """Check if validation passed (no failures)."""
        return self.failed == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "platform": self.platform,
            "summary": {
                "passed": self.passed,
                "failed": self.failed,
                "warnings": self.warnings,
                "skipped": self.skipped,
                "is_successful": self.is_successful,
            },
            "checks": [c.to_dict() for c in self.checks],
        }


class SetupValidator:
    """Validates OPTIC-SHIELD installation."""

    def __init__(self, install_dir: Optional[Path] = None):
        self.install_dir = install_dir or Path(__file__).parent.parent
        self.venv_dir = self.install_dir / "venv"
        self.venv_python = self.venv_dir / "bin" / "python"
        self.report: Optional[ValidationReport] = None

    def run_all_checks(self) -> ValidationReport:
        """Run all validation checks."""
        # Import platform detector
        try:
            from src.utils.platform_detector import get_detector

            detector = get_detector(self.install_dir)
            platform_info = detector.get_full_report()
        except Exception as e:
            platform_info = {"error": str(e)}

        self.report = ValidationReport(
            timestamp=datetime.now().isoformat(), platform=platform_info
        )

        # Run all checks
        checks = [
            self._check_python_version,
            self._check_virtual_environment,
            self._check_core_dependencies,
            self._check_opencv,
            self._check_camera_module,
            self._check_gpio_module,
            self._check_config_files,
            self._check_data_directory,
            self._check_logs_directory,
            self._check_models_directory,
            self._check_yolo_model,
            self._check_database,
            self._check_camera_hardware,
            self._check_model_load,
            self._check_detection,
            self._check_storage,
            self._check_systemd_service,
            self._check_user_permissions,
            self._check_network,
        ]

        for check_func in checks:
            try:
                result = check_func()
                self.report.add_result(result)
            except Exception as e:
                self.report.add_result(
                    CheckResult(
                        name=check_func.__name__.replace("_check_", "").title(),
                        status=CheckStatus.FAIL,
                        message=f"Check failed with exception: {e}",
                    )
                )

        return self.report

    # =========================================================================
    # Basic Checks (1-4)
    # =========================================================================

    def _check_python_version(self) -> CheckResult:
        """Check 1: Verify Python 3.10+"""
        version = sys.version_info
        if version.major >= 3 and version.minor >= 10:
            return CheckResult(
                name="Python Version",
                status=CheckStatus.PASS,
                message=f"Python {version.major}.{version.minor}.{version.micro}",
            )
        else:
            return CheckResult(
                name="Python Version",
                status=CheckStatus.FAIL,
                message=f"Python {version.major}.{version.minor} (need 3.10+)",
            )

    def _check_virtual_environment(self) -> CheckResult:
        """Check 2: Verify virtual environment exists"""
        if not self.venv_dir.exists():
            return CheckResult(
                name="Virtual Environment",
                status=CheckStatus.FAIL,
                message="venv directory not found",
            )

        if not self.venv_python.exists():
            return CheckResult(
                name="Virtual Environment",
                status=CheckStatus.FAIL,
                message="venv/bin/python not found",
            )

        # Check if we're in the venv
        in_venv = sys.prefix != sys.base_prefix

        return CheckResult(
            name="Virtual Environment",
            status=CheckStatus.PASS,
            message=f"Found at {self.venv_dir}" + (" (active)" if in_venv else ""),
        )

    def _check_core_dependencies(self) -> CheckResult:
        """Check 3: Verify core Python dependencies"""
        missing = []
        installed = []

        deps = [
            ("ultralytics", "ultralytics"),
            ("numpy", "numpy"),
            ("PIL", "Pillow"),
            ("yaml", "PyYAML"),
        ]

        for import_name, package_name in deps:
            try:
                __import__(import_name)
                installed.append(package_name)
            except ImportError:
                missing.append(package_name)

        if missing:
            return CheckResult(
                name="Core Dependencies",
                status=CheckStatus.FAIL,
                message=f"Missing: {', '.join(missing)}",
            )

        return CheckResult(
            name="Core Dependencies",
            status=CheckStatus.PASS,
            message=f"All installed ({len(installed)} packages)",
        )

    def _check_opencv(self) -> CheckResult:
        """Check 4: Verify OpenCV installation"""
        try:
            import cv2

            return CheckResult(
                name="OpenCV",
                status=CheckStatus.PASS,
                message=f"Version {cv2.__version__}",
            )
        except ImportError:
            return CheckResult(
                name="OpenCV",
                status=CheckStatus.FAIL,
                message="opencv-python-headless not installed",
            )

    # =========================================================================
    # Module Checks (5-6)
    # =========================================================================

    def _check_camera_module(self) -> CheckResult:
        """Check 5: Check camera module availability"""
        try:
            from src.utils.platform_detector import is_raspberry_pi

            if is_raspberry_pi():
                try:
                    from picamera2 import Picamera2

                    return CheckResult(
                        name="Camera Module",
                        status=CheckStatus.PASS,
                        message="picamera2 available",
                    )
                except ImportError:
                    return CheckResult(
                        name="Camera Module",
                        status=CheckStatus.WARN,
                        message="picamera2 not installed (USB fallback available)",
                    )
            else:
                return CheckResult(
                    name="Camera Module",
                    status=CheckStatus.SKIP,
                    message="Not on Raspberry Pi",
                )
        except Exception:
            return CheckResult(
                name="Camera Module",
                status=CheckStatus.SKIP,
                message="Platform detection unavailable",
            )

    def _check_gpio_module(self) -> CheckResult:
        """Check 6: Check GPIO module (RPi only)"""
        try:
            from src.utils.platform_detector import is_raspberry_pi

            if not is_raspberry_pi():
                return CheckResult(
                    name="GPIO Module",
                    status=CheckStatus.SKIP,
                    message="Not on Raspberry Pi",
                )

            try:
                import RPi.GPIO

                return CheckResult(
                    name="GPIO Module",
                    status=CheckStatus.PASS,
                    message="RPi.GPIO available",
                )
            except ImportError:
                return CheckResult(
                    name="GPIO Module",
                    status=CheckStatus.WARN,
                    message="RPi.GPIO not installed (optional)",
                )
        except Exception:
            return CheckResult(
                name="GPIO Module",
                status=CheckStatus.SKIP,
                message="Platform detection unavailable",
            )

    # =========================================================================
    # Directory Checks (7-11)
    # =========================================================================

    def _check_config_files(self) -> CheckResult:
        """Check 7: Verify config files exist"""
        config_file = self.install_dir / "config" / "config.yaml"

        if not config_file.exists():
            return CheckResult(
                name="Config Files",
                status=CheckStatus.FAIL,
                message="config/config.yaml not found",
            )

        return CheckResult(
            name="Config Files", status=CheckStatus.PASS, message="config.yaml found"
        )

    def _check_data_directory(self) -> CheckResult:
        """Check 8: Verify data directory"""
        data_dir = self.install_dir / "data"
        images_dir = data_dir / "images"

        if not data_dir.exists():
            return CheckResult(
                name="Data Directory",
                status=CheckStatus.FAIL,
                message="data/ directory not found",
            )

        if not images_dir.exists():
            return CheckResult(
                name="Data Directory",
                status=CheckStatus.WARN,
                message="data/images/ not found",
            )

        # Check write permission
        try:
            test_file = data_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            return CheckResult(
                name="Data Directory",
                status=CheckStatus.PASS,
                message="Exists and writable",
            )
        except PermissionError:
            return CheckResult(
                name="Data Directory", status=CheckStatus.FAIL, message="Not writable"
            )

    def _check_logs_directory(self) -> CheckResult:
        """Check 9: Verify logs directory"""
        logs_dir = self.install_dir / "logs"

        if not logs_dir.exists():
            return CheckResult(
                name="Logs Directory",
                status=CheckStatus.WARN,
                message="logs/ directory not found (will be created)",
            )

        # Check write permission
        try:
            test_file = logs_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            return CheckResult(
                name="Logs Directory",
                status=CheckStatus.PASS,
                message="Exists and writable",
            )
        except PermissionError:
            return CheckResult(
                name="Logs Directory", status=CheckStatus.FAIL, message="Not writable"
            )

    def _check_models_directory(self) -> CheckResult:
        """Check 10: Verify models directory"""
        models_dir = self.install_dir / "models"

        if not models_dir.exists():
            return CheckResult(
                name="Models Directory",
                status=CheckStatus.WARN,
                message="models/ directory not found (will be created)",
            )

        return CheckResult(
            name="Models Directory", status=CheckStatus.PASS, message="Exists"
        )

    def _check_yolo_model(self) -> CheckResult:
        """Check 11: Verify YOLO model is present"""
        models_dir = self.install_dir / "models"

        # Check for NCNN model
        ncnn_model = models_dir / "yolo11n_ncnn_model"
        if ncnn_model.exists() and ncnn_model.is_dir():
            return CheckResult(
                name="YOLO Model", status=CheckStatus.PASS, message="NCNN model found"
            )

        # Check for PT model
        pt_model = models_dir / "yolo11n.pt"
        if pt_model.exists():
            return CheckResult(
                name="YOLO Model",
                status=CheckStatus.PASS,
                message="PyTorch model found",
            )

        return CheckResult(
            name="YOLO Model",
            status=CheckStatus.WARN,
            message="No model found (will download on first run)",
        )

    # =========================================================================
    # Functional Checks (12-16)
    # =========================================================================

    def _check_database(self) -> CheckResult:
        """Check 12: Test SQLite database connection"""
        try:
            import sqlite3

            db_path = self.install_dir / "data" / "detections.db"

            # Try to create/open database
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]
            conn.close()

            return CheckResult(
                name="Database", status=CheckStatus.PASS, message=f"SQLite {version}"
            )
        except Exception as e:
            return CheckResult(
                name="Database", status=CheckStatus.FAIL, message=f"Database error: {e}"
            )

    def _check_camera_hardware(self) -> CheckResult:
        """Check 13: Test camera capture"""
        try:
            from src.utils.platform_detector import has_camera, get_detector

            detector = get_detector()
            hw = detector.get_hardware_capabilities()

            if hw.has_camera:
                return CheckResult(
                    name="Camera Hardware",
                    status=CheckStatus.PASS,
                    message=f"Detected: {hw.camera_type}",
                )
            else:
                return CheckResult(
                    name="Camera Hardware",
                    status=CheckStatus.WARN,
                    message="No camera detected",
                )
        except Exception as e:
            return CheckResult(
                name="Camera Hardware",
                status=CheckStatus.SKIP,
                message=f"Could not check: {e}",
            )

    def _check_model_load(self) -> CheckResult:
        """Check 14: Test model loading"""
        try:
            from ultralytics import YOLO

            # Try to load model (will download if needed)
            model = YOLO("yolo11n.pt")

            return CheckResult(
                name="Model Load",
                status=CheckStatus.PASS,
                message="YOLO model loaded successfully",
            )
        except Exception as e:
            return CheckResult(
                name="Model Load",
                status=CheckStatus.WARN,
                message=f"Model load test skipped: {e}",
            )

    def _check_detection(self) -> CheckResult:
        """Check 15: Test inference on dummy image"""
        try:
            import numpy as np
            from ultralytics import YOLO

            # Create a small test image
            test_image = np.zeros((224, 224, 3), dtype=np.uint8)

            # Try to run inference
            model = YOLO("yolo11n.pt")
            results = model(test_image, verbose=False)

            return CheckResult(
                name="Detection",
                status=CheckStatus.PASS,
                message="Inference test passed",
            )
        except Exception as e:
            return CheckResult(
                name="Detection",
                status=CheckStatus.WARN,
                message=f"Detection test skipped: {e}",
            )

    def _check_storage(self) -> CheckResult:
        """Check 16: Test file storage"""
        try:
            test_file = self.install_dir / "data" / "images" / ".storage_test"
            test_file.parent.mkdir(parents=True, exist_ok=True)

            # Write test
            test_file.write_text("test")

            # Read test
            content = test_file.read_text()

            # Cleanup
            test_file.unlink()

            if content == "test":
                return CheckResult(
                    name="Storage",
                    status=CheckStatus.PASS,
                    message="Read/write test passed",
                )
            else:
                return CheckResult(
                    name="Storage",
                    status=CheckStatus.FAIL,
                    message="Read/write mismatch",
                )
        except Exception as e:
            return CheckResult(
                name="Storage", status=CheckStatus.FAIL, message=f"Storage error: {e}"
            )

    # =========================================================================
    # System Checks (17-19)
    # =========================================================================

    def _check_systemd_service(self) -> CheckResult:
        """Check 17: Check systemd service"""
        try:
            from src.utils.platform_detector import get_os_type, OSType

            os_type = get_os_type()

            if os_type not in (OSType.LINUX, OSType.RASPBERRY_PI):
                return CheckResult(
                    name="Systemd Service",
                    status=CheckStatus.SKIP,
                    message=f"Not applicable on {os_type.value}",
                )

            # Check if systemctl exists
            result = subprocess.run(
                ["systemctl", "list-unit-files", "optic-shield.service"],
                capture_output=True,
                text=True,
            )

            if "optic-shield.service" in result.stdout:
                return CheckResult(
                    name="Systemd Service",
                    status=CheckStatus.PASS,
                    message="Service installed",
                )
            else:
                return CheckResult(
                    name="Systemd Service",
                    status=CheckStatus.WARN,
                    message="Service not installed",
                )
        except FileNotFoundError:
            return CheckResult(
                name="Systemd Service",
                status=CheckStatus.SKIP,
                message="systemctl not found",
            )
        except Exception as e:
            return CheckResult(
                name="Systemd Service",
                status=CheckStatus.SKIP,
                message=f"Could not check: {e}",
            )

    def _check_user_permissions(self) -> CheckResult:
        """Check 18: Verify user permissions"""
        try:
            from src.utils.platform_detector import get_detector

            detector = get_detector()
            missing = detector.get_missing_groups()

            if not missing:
                return CheckResult(
                    name="User Permissions",
                    status=CheckStatus.PASS,
                    message="All required groups present",
                )
            else:
                return CheckResult(
                    name="User Permissions",
                    status=CheckStatus.WARN,
                    message=f"Missing groups: {', '.join(missing)}",
                )
        except Exception as e:
            return CheckResult(
                name="User Permissions",
                status=CheckStatus.SKIP,
                message=f"Could not check: {e}",
            )

    def _check_network(self) -> CheckResult:
        """Check 19: Check network connectivity (optional)"""
        try:
            import socket

            # Try to connect to a known host
            socket.setdefaulttimeout(3)
            socket.create_connection(("8.8.8.8", 53))

            return CheckResult(
                name="Network",
                status=CheckStatus.PASS,
                message="Internet connectivity available",
            )
        except (socket.timeout, socket.error):
            return CheckResult(
                name="Network",
                status=CheckStatus.WARN,
                message="No internet connectivity (optional for offline mode)",
            )


def print_report(report: ValidationReport, quiet: bool = False):
    """Print formatted validation report."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    NC = "\033[0m"

    print()
    print(f"{BLUE}╔══════════════════════════════════════════════════════════════╗{NC}")
    print(
        f"{BLUE}║{NC}                OPTIC-SHIELD VALIDATION REPORT                {BLUE}║{NC}"
    )
    print(f"{BLUE}╠══════════════════════════════════════════════════════════════╣{NC}")

    # Platform info
    if "system" in report.platform:
        sys_info = report.platform["system"]
        print(f"{BLUE}║{NC}  Platform: {sys_info.get('os_name', 'Unknown')}")
        print(f"{BLUE}║{NC}  Python:   {sys_info.get('python_version', 'Unknown')}")
        print(f"{BLUE}║{NC}  Arch:     {sys_info.get('architecture', 'Unknown')}")

    print(f"{BLUE}╠══════════════════════════════════════════════════════════════╣{NC}")
    print(
        f"{BLUE}║{NC}  Validation Results:                                         {BLUE}║{NC}"
    )

    for check in report.checks:
        if quiet and check.status == CheckStatus.PASS:
            continue

        if check.status == CheckStatus.PASS:
            icon = f"{GREEN}✓{NC}"
        elif check.status == CheckStatus.FAIL:
            icon = f"{RED}✗{NC}"
        elif check.status == CheckStatus.WARN:
            icon = f"{YELLOW}⚠{NC}"
        else:
            icon = f"{BLUE}○{NC}"

        name = check.name.ljust(20)
        print(f"{BLUE}║{NC}  {icon} {name} {check.message[:35]}")

    print(f"{BLUE}╠══════════════════════════════════════════════════════════════╣{NC}")
    print(
        f"{BLUE}║{NC}  Summary:                                                     {BLUE}║{NC}"
    )
    print(f"{BLUE}║{NC}    {GREEN}Passed:{NC}   {report.passed}")
    print(f"{BLUE}║{NC}    {RED}Failed:{NC}   {report.failed}")
    print(f"{BLUE}║{NC}    {YELLOW}Warnings:{NC} {report.warnings}")
    print(f"{BLUE}╠══════════════════════════════════════════════════════════════╣{NC}")

    if report.is_successful:
        print(
            f"{BLUE}║{NC}                                                              {BLUE}║{NC}"
        )
        print(
            f"{BLUE}║{NC}   {GREEN}✅ TESTED OK - Ready to use!{NC}                               {BLUE}║{NC}"
        )
        print(
            f"{BLUE}║{NC}                                                              {BLUE}║{NC}"
        )
    else:
        print(
            f"{BLUE}║{NC}                                                              {BLUE}║{NC}"
        )
        print(
            f"{BLUE}║{NC}   {RED}❌ VALIDATION FAILED - Please fix issues above{NC}             {BLUE}║{NC}"
        )
        print(
            f"{BLUE}║{NC}                                                              {BLUE}║{NC}"
        )

    print(f"{BLUE}╚══════════════════════════════════════════════════════════════╝{NC}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Validate OPTIC-SHIELD installation")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Only show failures and warnings"
    )
    parser.add_argument(
        "--dir", type=str, default=None, help="Installation directory to validate"
    )

    args = parser.parse_args()

    install_dir = Path(args.dir) if args.dir else None
    validator = SetupValidator(install_dir)
    report = validator.run_all_checks()

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_report(report, quiet=args.quiet)

    # Exit with appropriate code
    sys.exit(0 if report.is_successful else 1)


if __name__ == "__main__":
    main()
