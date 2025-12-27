"""
Platform detection utilities for OPTIC-SHIELD.
Automatically detects OS type, user groups, paths, and hardware capabilities.
"""

import os
import sys
import platform
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class OSType(Enum):
    """Supported operating system types."""

    RASPBERRY_PI = "raspberry_pi"
    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


class Architecture(Enum):
    """CPU architecture types."""

    ARM64 = "arm64"
    ARM32 = "arm32"
    X86_64 = "x86_64"
    X86 = "x86"
    UNKNOWN = "unknown"


@dataclass
class UserInfo:
    """User and group information."""

    username: str
    uid: int
    gid: int
    home_dir: str
    groups: List[str] = field(default_factory=list)
    is_root: bool = False

    def has_group(self, group_name: str) -> bool:
        """Check if user belongs to a specific group."""
        return group_name in self.groups

    def to_dict(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "uid": self.uid,
            "gid": self.gid,
            "home_dir": self.home_dir,
            "groups": self.groups,
            "is_root": self.is_root,
        }


@dataclass
class SystemInfo:
    """System hardware and software information."""

    os_type: OSType
    os_name: str
    os_version: str
    architecture: Architecture
    cpu_count: int
    memory_gb: float
    kernel: str
    hostname: str
    python_version: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "os_type": self.os_type.value,
            "os_name": self.os_name,
            "os_version": self.os_version,
            "architecture": self.architecture.value,
            "cpu_count": self.cpu_count,
            "memory_gb": round(self.memory_gb, 2),
            "kernel": self.kernel,
            "hostname": self.hostname,
            "python_version": self.python_version,
        }


@dataclass
class PathInfo:
    """Path configuration based on platform."""

    install_dir: Path
    data_dir: Path
    log_dir: Path
    config_dir: Path
    models_dir: Path
    venv_dir: Path

    def to_dict(self) -> Dict[str, str]:
        return {
            "install_dir": str(self.install_dir),
            "data_dir": str(self.data_dir),
            "log_dir": str(self.log_dir),
            "config_dir": str(self.config_dir),
            "models_dir": str(self.models_dir),
            "venv_dir": str(self.venv_dir),
        }


@dataclass
class HardwareCapabilities:
    """Hardware capability detection results."""

    has_camera: bool = False
    camera_type: Optional[str] = None
    has_gpio: bool = False
    has_i2c: bool = False
    has_spi: bool = False
    can_run_ncnn: bool = False
    gpu_available: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_camera": self.has_camera,
            "camera_type": self.camera_type,
            "has_gpio": self.has_gpio,
            "has_i2c": self.has_i2c,
            "has_spi": self.has_spi,
            "can_run_ncnn": self.can_run_ncnn,
            "gpu_available": self.gpu_available,
        }


class PlatformDetector:
    """
    Comprehensive platform detection for OPTIC-SHIELD.
    Automatically detects OS, user, paths, and hardware capabilities.
    """

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path(__file__).parent.parent.parent
        self._os_type: Optional[OSType] = None
        self._user_info: Optional[UserInfo] = None
        self._system_info: Optional[SystemInfo] = None
        self._path_info: Optional[PathInfo] = None
        self._hardware: Optional[HardwareCapabilities] = None

    # -------------------------------------------------------------------------
    # OS Detection
    # -------------------------------------------------------------------------

    def get_os_type(self) -> OSType:
        """Detect the operating system type."""
        if self._os_type is not None:
            return self._os_type

        system = platform.system().lower()

        if system == "darwin":
            self._os_type = OSType.MACOS
        elif system == "windows":
            self._os_type = OSType.WINDOWS
        elif system == "linux":
            # Check if it's a Raspberry Pi
            if self._is_raspberry_pi():
                self._os_type = OSType.RASPBERRY_PI
            else:
                self._os_type = OSType.LINUX
        else:
            self._os_type = OSType.UNKNOWN

        logger.debug(f"Detected OS type: {self._os_type.value}")
        return self._os_type

    def _is_raspberry_pi(self) -> bool:
        """Check if running on a Raspberry Pi."""
        # Check /proc/cpuinfo for Raspberry Pi
        try:
            with open("/proc/cpuinfo", "r") as f:
                cpuinfo = f.read().lower()
                if "raspberry pi" in cpuinfo or "bcm" in cpuinfo:
                    return True
        except (FileNotFoundError, PermissionError):
            pass

        # Check /proc/device-tree/model
        try:
            with open("/proc/device-tree/model", "r") as f:
                model = f.read().lower()
                if "raspberry pi" in model:
                    return True
        except (FileNotFoundError, PermissionError):
            pass

        # Check for Raspberry Pi specific files
        rpi_indicators = ["/opt/vc/bin/vcgencmd", "/sys/firmware/devicetree/base/model"]
        for indicator in rpi_indicators:
            if os.path.exists(indicator):
                return True

        return False

    def is_raspberry_pi(self) -> bool:
        """Public method to check if running on Raspberry Pi."""
        return self.get_os_type() == OSType.RASPBERRY_PI

    def get_architecture(self) -> Architecture:
        """Detect CPU architecture."""
        machine = platform.machine().lower()

        if machine in ("aarch64", "arm64"):
            return Architecture.ARM64
        elif machine.startswith("arm"):
            return Architecture.ARM32
        elif machine in ("x86_64", "amd64"):
            return Architecture.X86_64
        elif machine in ("i386", "i686", "x86"):
            return Architecture.X86
        else:
            return Architecture.UNKNOWN

    # -------------------------------------------------------------------------
    # User Detection
    # -------------------------------------------------------------------------

    def get_user_info(self) -> UserInfo:
        """Get current user information including groups."""
        if self._user_info is not None:
            return self._user_info

        os_type = self.get_os_type()

        if os_type == OSType.WINDOWS:
            self._user_info = self._get_windows_user_info()
        else:
            self._user_info = self._get_unix_user_info()

        logger.debug(
            f"Detected user: {self._user_info.username}, groups: {self._user_info.groups}"
        )
        return self._user_info

    def _get_unix_user_info(self) -> UserInfo:
        """Get user info on Unix-like systems."""
        import pwd
        import grp

        uid = os.getuid()
        gid = os.getgid()
        pw = pwd.getpwuid(uid)

        # Get all groups the user belongs to
        groups = []
        try:
            # Get supplementary groups
            group_ids = os.getgroups()
            for gid_item in group_ids:
                try:
                    groups.append(grp.getgrgid(gid_item).gr_name)
                except KeyError:
                    pass

            # Also check common hardware groups
            for group_name in ["video", "gpio", "i2c", "spi", "dialout", "plugdev"]:
                try:
                    gr = grp.getgrnam(group_name)
                    if pw.pw_name in gr.gr_mem or gid == gr.gr_gid:
                        if group_name not in groups:
                            groups.append(group_name)
                except KeyError:
                    pass
        except Exception as e:
            logger.warning(f"Error getting user groups: {e}")

        return UserInfo(
            username=pw.pw_name,
            uid=uid,
            gid=gid,
            home_dir=pw.pw_dir,
            groups=sorted(set(groups)),
            is_root=(uid == 0),
        )

    def _get_windows_user_info(self) -> UserInfo:
        """Get user info on Windows."""
        username = os.environ.get("USERNAME", "unknown")
        home_dir = os.environ.get("USERPROFILE", os.path.expanduser("~"))

        return UserInfo(
            username=username,
            uid=0,
            gid=0,
            home_dir=home_dir,
            groups=["Users"],
            is_root=False,
        )

    def get_required_groups(self) -> List[str]:
        """Get list of required groups for the current platform."""
        os_type = self.get_os_type()

        if os_type == OSType.RASPBERRY_PI:
            return ["video", "gpio", "i2c"]
        elif os_type == OSType.LINUX:
            return ["video"]
        else:
            return []

    def get_missing_groups(self) -> List[str]:
        """Get list of groups the user is missing."""
        required = self.get_required_groups()
        user_info = self.get_user_info()
        return [g for g in required if not user_info.has_group(g)]

    # -------------------------------------------------------------------------
    # System Info
    # -------------------------------------------------------------------------

    def get_system_info(self) -> SystemInfo:
        """Get comprehensive system information."""
        if self._system_info is not None:
            return self._system_info

        os_type = self.get_os_type()

        # Get OS name and version
        if os_type == OSType.MACOS:
            os_name = "macOS"
            os_version = platform.mac_ver()[0]
        elif os_type == OSType.WINDOWS:
            os_name = "Windows"
            os_version = platform.win32_ver()[0]
        elif os_type in (OSType.LINUX, OSType.RASPBERRY_PI):
            os_name, os_version = self._get_linux_distro_info()
        else:
            os_name = platform.system()
            os_version = platform.release()

        # Get memory
        memory_gb = self._get_memory_gb()

        self._system_info = SystemInfo(
            os_type=os_type,
            os_name=os_name,
            os_version=os_version,
            architecture=self.get_architecture(),
            cpu_count=os.cpu_count() or 1,
            memory_gb=memory_gb,
            kernel=platform.release(),
            hostname=platform.node(),
            python_version=platform.python_version(),
        )

        return self._system_info

    def _get_linux_distro_info(self) -> tuple:
        """Get Linux distribution name and version."""
        try:
            with open("/etc/os-release", "r") as f:
                lines = f.readlines()

            info = {}
            for line in lines:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    info[key] = value.strip('"')

            name = info.get("PRETTY_NAME", info.get("NAME", "Linux"))
            version = info.get("VERSION_ID", "")
            return name, version
        except Exception:
            return "Linux", ""

    def _get_memory_gb(self) -> float:
        """Get total system memory in GB."""
        os_type = self.get_os_type()

        if os_type == OSType.WINDOWS:
            try:
                import ctypes

                kernel32 = ctypes.windll.kernel32
                c_ulong = ctypes.c_ulong

                class MEMORYSTATUS(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", c_ulong),
                        ("dwMemoryLoad", c_ulong),
                        ("dwTotalPhys", c_ulong),
                        ("dwAvailPhys", c_ulong),
                        ("dwTotalPageFile", c_ulong),
                        ("dwAvailPageFile", c_ulong),
                        ("dwTotalVirtual", c_ulong),
                        ("dwAvailVirtual", c_ulong),
                    ]

                memory_status = MEMORYSTATUS()
                memory_status.dwLength = ctypes.sizeof(MEMORYSTATUS)
                kernel32.GlobalMemoryStatus(ctypes.byref(memory_status))
                return memory_status.dwTotalPhys / (1024**3)
            except Exception:
                return 0.0
        else:
            try:
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            kb = int(line.split()[1])
                            return kb / (1024**2)
            except Exception:
                pass

            # Fallback for macOS
            try:
                result = subprocess.run(
                    ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True
                )
                if result.returncode == 0:
                    return int(result.stdout.strip()) / (1024**3)
            except Exception:
                pass

        return 0.0

    # -------------------------------------------------------------------------
    # Path Detection
    # -------------------------------------------------------------------------

    def get_paths(self) -> PathInfo:
        """Get platform-appropriate paths."""
        if self._path_info is not None:
            return self._path_info

        install_dir = self.base_path

        self._path_info = PathInfo(
            install_dir=install_dir,
            data_dir=install_dir / "data",
            log_dir=install_dir / "logs",
            config_dir=install_dir / "config",
            models_dir=install_dir / "models",
            venv_dir=install_dir / "venv",
        )

        return self._path_info

    # -------------------------------------------------------------------------
    # Hardware Detection
    # -------------------------------------------------------------------------

    def get_hardware_capabilities(self) -> HardwareCapabilities:
        """Detect available hardware capabilities."""
        if self._hardware is not None:
            return self._hardware

        self._hardware = HardwareCapabilities(
            has_camera=self._detect_camera(),
            camera_type=self._detect_camera_type(),
            has_gpio=self._detect_gpio(),
            has_i2c=self._detect_i2c(),
            has_spi=self._detect_spi(),
            can_run_ncnn=self._can_run_ncnn(),
            gpu_available=self._detect_gpu(),
        )

        return self._hardware

    def _detect_camera(self) -> bool:
        """Check if any camera is available."""
        # Check for Pi Camera
        if self._detect_pi_camera():
            return True

        # Check for USB cameras
        if self._detect_usb_camera():
            return True

        return False

    def _detect_camera_type(self) -> Optional[str]:
        """Detect the type of camera available."""
        if self._detect_pi_camera():
            return "pi_camera"
        elif self._detect_usb_camera():
            return "usb_camera"
        return None

    def _detect_pi_camera(self) -> bool:
        """Check if Pi Camera is available."""
        if not self.is_raspberry_pi():
            return False

        try:
            # Check libcamera
            result = subprocess.run(
                ["libcamera-hello", "--list-cameras"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and "Available cameras" in result.stdout:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Check legacy camera interface
        try:
            result = subprocess.run(
                ["vcgencmd", "get_camera"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and "detected=1" in result.stdout:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return False

    def _detect_usb_camera(self) -> bool:
        """Check if USB camera is available."""
        # Check /dev/video* devices
        import glob

        video_devices = glob.glob("/dev/video*")
        if video_devices:
            return True

        # Try OpenCV
        try:
            import cv2

            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                cap.release()
                return True
        except Exception:
            pass

        return False

    def _detect_gpio(self) -> bool:
        """Check if GPIO is available."""
        if not self.is_raspberry_pi():
            return False

        # Check for GPIO sysfs
        if os.path.exists("/sys/class/gpio"):
            return True

        # Check for gpiochip
        import glob

        if glob.glob("/dev/gpiochip*"):
            return True

        return False

    def _detect_i2c(self) -> bool:
        """Check if I2C is available."""
        import glob

        return bool(glob.glob("/dev/i2c-*"))

    def _detect_spi(self) -> bool:
        """Check if SPI is available."""
        import glob

        return bool(glob.glob("/dev/spidev*"))

    def _can_run_ncnn(self) -> bool:
        """Check if NCNN can run on this platform."""
        arch = self.get_architecture()
        return arch in (Architecture.ARM64, Architecture.X86_64)

    def _detect_gpu(self) -> bool:
        """Check if GPU acceleration is available."""
        os_type = self.get_os_type()

        if os_type == OSType.RASPBERRY_PI:
            # Check VideoCore
            try:
                result = subprocess.run(
                    ["vcgencmd", "get_mem", "gpu"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.returncode == 0
            except Exception:
                pass

        # Check for CUDA
        try:
            import torch

            return torch.cuda.is_available()
        except ImportError:
            pass

        return False

    def has_camera(self) -> bool:
        """Check if camera is available."""
        return self.get_hardware_capabilities().has_camera

    def has_gpio(self) -> bool:
        """Check if GPIO is available."""
        return self.get_hardware_capabilities().has_gpio

    def can_run_ncnn(self) -> bool:
        """Check if NCNN can run effectively."""
        return self.get_hardware_capabilities().can_run_ncnn

    # -------------------------------------------------------------------------
    # Full Platform Report
    # -------------------------------------------------------------------------

    def get_full_report(self) -> Dict[str, Any]:
        """Get a complete platform detection report."""
        return {
            "system": self.get_system_info().to_dict(),
            "user": self.get_user_info().to_dict(),
            "paths": self.get_paths().to_dict(),
            "hardware": self.get_hardware_capabilities().to_dict(),
            "missing_groups": self.get_missing_groups(),
        }

    def print_report(self):
        """Print a formatted platform report."""
        report = self.get_full_report()
        sys_info = report["system"]
        user_info = report["user"]
        hw_info = report["hardware"]

        print("=" * 60)
        print("OPTIC-SHIELD Platform Detection Report")
        print("=" * 60)
        print(f"OS Type:        {sys_info['os_type']}")
        print(f"OS Name:        {sys_info['os_name']} {sys_info['os_version']}")
        print(f"Architecture:   {sys_info['architecture']}")
        print(f"CPU Cores:      {sys_info['cpu_count']}")
        print(f"Memory:         {sys_info['memory_gb']} GB")
        print(f"Python:         {sys_info['python_version']}")
        print("-" * 60)
        print(f"User:           {user_info['username']}")
        print(f"Groups:         {', '.join(user_info['groups']) or 'None detected'}")
        print(f"Is Root:        {user_info['is_root']}")
        print("-" * 60)
        print(
            f"Camera:         {'✓ ' + (hw_info['camera_type'] or '') if hw_info['has_camera'] else '✗ Not detected'}"
        )
        print(f"GPIO:           {'✓' if hw_info['has_gpio'] else '✗'}")
        print(f"I2C:            {'✓' if hw_info['has_i2c'] else '✗'}")
        print(f"NCNN Support:   {'✓' if hw_info['can_run_ncnn'] else '✗'}")
        print("=" * 60)

        missing = report["missing_groups"]
        if missing:
            print(f"\n⚠️  Missing groups: {', '.join(missing)}")
            print(
                "   Run: sudo usermod -aG "
                + ",".join(missing)
                + f" {user_info['username']}"
            )


# Singleton instance
_detector: Optional[PlatformDetector] = None


def get_detector(base_path: Optional[Path] = None) -> PlatformDetector:
    """Get or create the platform detector singleton."""
    global _detector
    if _detector is None:
        _detector = PlatformDetector(base_path)
    return _detector


# Convenience functions
def get_os_type() -> OSType:
    """Get the detected OS type."""
    return get_detector().get_os_type()


def is_raspberry_pi() -> bool:
    """Check if running on Raspberry Pi."""
    return get_detector().is_raspberry_pi()


def get_user_info() -> UserInfo:
    """Get current user information."""
    return get_detector().get_user_info()


def get_system_info() -> SystemInfo:
    """Get system information."""
    return get_detector().get_system_info()


def get_paths() -> PathInfo:
    """Get platform paths."""
    return get_detector().get_paths()


def has_camera() -> bool:
    """Check if camera is available."""
    return get_detector().has_camera()


def has_gpio() -> bool:
    """Check if GPIO is available."""
    return get_detector().has_gpio()


def can_run_ncnn() -> bool:
    """Check if NCNN is supported."""
    return get_detector().can_run_ncnn()


if __name__ == "__main__":
    # Run platform detection and print report
    detector = PlatformDetector()
    detector.print_report()
