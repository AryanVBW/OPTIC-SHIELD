"""
Dependency checker and auto-installer for OPTIC-SHIELD.
Ensures all required packages are installed before the main application starts.
"""

import subprocess
import sys
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


# Core dependencies required for OPTIC-SHIELD
REQUIRED_PACKAGES: Dict[str, str] = {
    "ultralytics": "ultralytics>=8.0.0",
    "numpy": "numpy<2.0",
    "PIL": "Pillow>=9.0.0",
    "yaml": "PyYAML>=6.0",
    "cv2": "opencv-python-headless>=4.5.0",
    "requests": "requests>=2.28.0",
}

# Optional packages (won't fail if not installed)
OPTIONAL_PACKAGES: Dict[str, str] = {
    "picamera2": "picamera2",  # Raspberry Pi only
    "RPi": "RPi.GPIO",  # Raspberry Pi only
}


class DependencyChecker:
    """
    Checks and auto-installs missing dependencies.
    """
    
    def __init__(self, auto_install: bool = True, quiet: bool = False):
        """
        Initialize the dependency checker.
        
        Args:
            auto_install: Whether to automatically install missing packages
            quiet: Whether to suppress pip output
        """
        self.auto_install = auto_install
        self.quiet = quiet
        self._missing: List[str] = []
        self._installed: List[str] = []
        self._failed: List[str] = []
    
    def check_package(self, import_name: str) -> bool:
        """
        Check if a package can be imported.
        
        Args:
            import_name: The name used to import the package
            
        Returns:
            True if package is available
        """
        try:
            __import__(import_name)
            return True
        except ImportError:
            return False
    
    def install_package(self, pip_name: str) -> bool:
        """
        Install a package using pip.
        
        Args:
            pip_name: The pip package name/specifier
            
        Returns:
            True if installation succeeded
        """
        try:
            cmd = [sys.executable, "-m", "pip", "install", pip_name]
            if self.quiet:
                cmd.append("--quiet")
            
            logger.info(f"Installing {pip_name}...")
            subprocess.check_call(cmd)
            logger.info(f"Successfully installed {pip_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install {pip_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error installing {pip_name}: {e}")
            return False
    
    def check_all(self) -> Tuple[List[str], List[str]]:
        """
        Check all required packages.
        
        Returns:
            Tuple of (available_packages, missing_packages)
        """
        available = []
        missing = []
        
        for import_name, pip_name in REQUIRED_PACKAGES.items():
            if self.check_package(import_name):
                available.append(import_name)
            else:
                missing.append((import_name, pip_name))
        
        return available, missing
    
    def ensure_dependencies(self) -> bool:
        """
        Ensure all dependencies are available, installing if necessary.
        
        Returns:
            True if all required dependencies are available
        """
        self._missing = []
        self._installed = []
        self._failed = []
        
        available, missing = self.check_all()
        
        if not missing:
            logger.info("All required dependencies are available")
            return True
        
        logger.warning(f"Missing packages: {[m[0] for m in missing]}")
        
        if not self.auto_install:
            self._missing = [m[1] for m in missing]
            logger.error("Auto-install disabled. Please install manually:")
            logger.error(f"  pip install {' '.join(self._missing)}")
            return False
        
        # Try to install missing packages
        for import_name, pip_name in missing:
            if self.install_package(pip_name):
                self._installed.append(pip_name)
            else:
                self._failed.append(pip_name)
        
        # Verify installations
        still_missing = []
        for import_name, pip_name in missing:
            if not self.check_package(import_name):
                still_missing.append(pip_name)
        
        if still_missing:
            logger.error(f"Failed to install: {still_missing}")
            self._failed = still_missing
            return False
        
        logger.info("All dependencies installed successfully")
        return True
    
    def get_status_report(self) -> Dict[str, List[str]]:
        """
        Get a detailed status report of dependencies.
        
        Returns:
            Dictionary with 'available', 'installed', 'failed' lists
        """
        available, _ = self.check_all()
        return {
            "available": available,
            "installed": self._installed,
            "failed": self._failed,
            "missing": self._missing
        }
    
    @staticmethod
    def get_package_version(import_name: str) -> Optional[str]:
        """
        Get the installed version of a package.
        
        Args:
            import_name: The name used to import the package
            
        Returns:
            Version string or None if not available
        """
        try:
            module = __import__(import_name)
            return getattr(module, "__version__", "unknown")
        except ImportError:
            return None


def check_and_install_dependencies(auto_install: bool = True) -> bool:
    """
    Convenience function to check and install all dependencies.
    
    Args:
        auto_install: Whether to automatically install missing packages
        
    Returns:
        True if all dependencies are available
    """
    checker = DependencyChecker(auto_install=auto_install)
    return checker.ensure_dependencies()


def print_dependency_status():
    """Print the status of all dependencies to console."""
    checker = DependencyChecker(auto_install=False)
    available, missing = checker.check_all()
    
    print("\n=== OPTIC-SHIELD Dependency Status ===\n")
    
    print("Available packages:")
    for pkg in available:
        version = checker.get_package_version(pkg)
        print(f"  ✓ {pkg}: {version}")
    
    if missing:
        print("\nMissing packages:")
        for import_name, pip_name in missing:
            print(f"  ✗ {import_name} ({pip_name})")
        print(f"\nTo install missing packages, run:")
        print(f"  pip install {' '.join([m[1] for m in missing])}")
    else:
        print("\n✓ All required dependencies are installed!")
    
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Check and install OPTIC-SHIELD dependencies")
    parser.add_argument("--install", action="store_true", help="Auto-install missing packages")
    parser.add_argument("--status", action="store_true", help="Show dependency status")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    if args.status:
        print_dependency_status()
    elif args.install:
        success = check_and_install_dependencies(auto_install=True)
        sys.exit(0 if success else 1)
    else:
        print_dependency_status()
