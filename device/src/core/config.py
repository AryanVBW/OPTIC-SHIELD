"""
Configuration management for OPTIC-SHIELD.
Supports layered configuration with environment-specific overrides.
Integrates with platform detection for auto-configuration.
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass, field

import yaml

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependencies
if TYPE_CHECKING:
    from src.utils.platform_detector import PlatformDetector


def deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@dataclass
class DeviceConfig:
    id: str = ""
    name: str = "optic-shield-001"
    location_name: str = "Unknown Location"
    latitude: float = 0.0
    longitude: float = 0.0


@dataclass
class ModelConfig:
    path: str = "models/yolo11n_ncnn_model"
    fallback_path: str = "models/yolo11n.pt"
    confidence_threshold: float = 0.5
    iou_threshold: float = 0.45
    max_detections: int = 10


@dataclass
class DetectionConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    target_classes: list = field(
        default_factory=lambda: [15, 16, 17, 18, 19, 20, 21, 22, 23]
    )
    input_size: int = 640
    batch_size: int = 1
    use_ncnn: bool = True
    num_threads: int = 4


@dataclass
class CameraConfig:
    enabled: bool = True
    width: int = 640
    height: int = 480
    format: str = "RGB888"
    fps: int = 10
    rotation: int = 0
    # Multi-camera auto-detection (NEW!)
    multi_camera_enabled: bool = True  # Auto-detect all cameras
    max_cameras: int = 10  # Maximum cameras to detect
    # Legacy single-camera settings
    fallback_usb: bool = True
    usb_device_id: int = 0


@dataclass
class DatabaseConfig:
    path: str = "data/detections.db"
    max_size_mb: int = 500


@dataclass
class ImageStorageConfig:
    path: str = "data/images"
    save_detections: bool = True
    jpeg_quality: int = 85
    max_storage_mb: int = 2000
    cleanup_days: int = 30


@dataclass
class StorageConfig:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    images: ImageStorageConfig = field(default_factory=ImageStorageConfig)
    logs_path: str = "logs"
    logs_max_size_mb: int = 100
    logs_retention_days: int = 7


@dataclass
class LocalAlertConfig:
    gpio_enabled: bool = False
    gpio_pin: int = 17
    buzzer_duration_ms: int = 500


@dataclass
class RemoteAlertConfig:
    enabled: bool = True
    include_image: bool = True
    image_max_size_kb: int = 100
    retry_attempts: int = 3
    retry_delay_seconds: int = 5


@dataclass
class AlertConfig:
    enabled: bool = True
    cooldown_seconds: int = 60
    local: LocalAlertConfig = field(default_factory=LocalAlertConfig)
    remote: RemoteAlertConfig = field(default_factory=RemoteAlertConfig)


@dataclass
class DashboardConfig:
    api_url: str = ""
    api_key: str = ""
    websocket_enabled: bool = True
    websocket_url: str = ""
    sync_interval_seconds: int = 300
    heartbeat_interval_seconds: int = 60
    offline_queue_max_size: int = 1000


@dataclass
class WatchdogConfig:
    enabled: bool = True
    timeout_seconds: int = 30


@dataclass
class SystemConfig:
    watchdog: WatchdogConfig = field(default_factory=WatchdogConfig)
    auto_restart: bool = True
    max_restart_attempts: int = 5
    restart_delay_seconds: int = 10
    max_memory_mb: int = 512
    max_cpu_percent: int = 80
    shutdown_timeout_seconds: int = 10


@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    console: bool = True
    file: bool = True
    file_path: str = "logs/optic-shield.log"


@dataclass
class UpdateConfig:
    """Configuration for update service."""
    enabled: bool = False  # Disabled by default - portal-triggered only
    remote: str = "origin"
    branch: str = "main"
    check_interval_seconds: int = 0  # 0 = no auto-check
    auto_update: bool = False
    service_name: str = "optic-shield"
    report_to_portal: bool = True


class Config:
    """Main configuration class with environment support."""

    _instance: Optional["Config"] = None

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path(__file__).parent.parent.parent / "config"
        self.environment = os.getenv("OPTIC_ENV", "development")
        self._raw_config: Dict[str, Any] = {}

        self.device = DeviceConfig()
        self.detection = DetectionConfig()
        self.camera = CameraConfig()
        self.storage = StorageConfig()
        self.alerts = AlertConfig()
        self.dashboard = DashboardConfig()
        self.system = SystemConfig()
        self.logging = LoggingConfig()
        self.updates = UpdateConfig()

        self._load_config()
        self._apply_env_overrides()
        self._ensure_device_id()

    @classmethod
    def get_instance(cls, config_dir: Optional[Path] = None) -> "Config":
        """Get singleton instance of Config."""
        if cls._instance is None:
            cls._instance = cls(config_dir)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (for testing)."""
        cls._instance = None

    def _load_config(self):
        """Load and merge configuration files."""
        base_config = self._load_yaml("config.yaml")
        env_config = self._load_yaml(f"config.{self.environment}.yaml")

        self._raw_config = deep_merge(base_config, env_config)
        self._parse_config()

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load a YAML configuration file."""
        filepath = self.config_dir / filename
        if not filepath.exists():
            logger.warning(f"Config file not found: {filepath}")
            return {}

        try:
            with open(filepath, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error loading config file {filepath}: {e}")
            return {}

    def _parse_config(self):
        """Parse raw config into dataclass objects."""
        cfg = self._raw_config

        if "device" in cfg:
            d = cfg["device"]
            loc = d.get("location", {})
            self.device = DeviceConfig(
                id=d.get("id", ""),
                name=d.get("name", "optic-shield-001"),
                location_name=loc.get("name", "Unknown Location"),
                latitude=loc.get("latitude", 0.0),
                longitude=loc.get("longitude", 0.0),
            )

        if "detection" in cfg:
            d = cfg["detection"]
            m = d.get("model", {})
            self.detection = DetectionConfig(
                model=ModelConfig(
                    path=m.get("path", "models/yolo11n_ncnn_model"),
                    fallback_path=m.get("fallback_path", "models/yolo11n.pt"),
                    confidence_threshold=m.get("confidence_threshold", 0.5),
                    iou_threshold=m.get("iou_threshold", 0.45),
                    max_detections=m.get("max_detections", 10),
                ),
                target_classes=d.get(
                    "target_classes", [14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
                ),
                input_size=d.get("input_size", 640),
                batch_size=d.get("batch_size", 1),
                use_ncnn=d.get("use_ncnn", True),
                num_threads=d.get("num_threads", 4),
            )

        if "camera" in cfg:
            c = cfg["camera"]
            res = c.get("resolution", {})
            self.camera = CameraConfig(
                enabled=c.get("enabled", True),
                width=res.get("width", 640),
                height=res.get("height", 480),
                format=c.get("format", "RGB888"),
                fps=c.get("fps", 10),
                rotation=c.get("rotation", 0),
                multi_camera_enabled=c.get("multi_camera_enabled", True),
                max_cameras=c.get("max_cameras", 10),
                fallback_usb=c.get("fallback_usb", True),
                usb_device_id=c.get("usb_device_id", 0),
            )

        if "storage" in cfg:
            s = cfg["storage"]
            db = s.get("database", {})
            img = s.get("images", {})
            logs = s.get("logs", {})
            self.storage = StorageConfig(
                database=DatabaseConfig(
                    path=db.get("path", "data/detections.db"),
                    max_size_mb=db.get("max_size_mb", 500),
                ),
                images=ImageStorageConfig(
                    path=img.get("path", "data/images"),
                    save_detections=img.get("save_detections", True),
                    jpeg_quality=img.get("jpeg_quality", 85),
                    max_storage_mb=img.get("max_storage_mb", 2000),
                    cleanup_days=img.get("cleanup_days", 30),
                ),
                logs_path=logs.get("path", "logs"),
                logs_max_size_mb=logs.get("max_size_mb", 100),
                logs_retention_days=logs.get("retention_days", 7),
            )

        if "alerts" in cfg:
            a = cfg["alerts"]
            loc = a.get("local", {})
            rem = a.get("remote", {})
            self.alerts = AlertConfig(
                enabled=a.get("enabled", True),
                cooldown_seconds=a.get("cooldown_seconds", 60),
                local=LocalAlertConfig(
                    gpio_enabled=loc.get("gpio_enabled", False),
                    gpio_pin=loc.get("gpio_pin", 17),
                    buzzer_duration_ms=loc.get("buzzer_duration_ms", 500),
                ),
                remote=RemoteAlertConfig(
                    enabled=rem.get("enabled", True),
                    include_image=rem.get("include_image", True),
                    image_max_size_kb=rem.get("image_max_size_kb", 100),
                    retry_attempts=rem.get("retry_attempts", 3),
                    retry_delay_seconds=rem.get("retry_delay_seconds", 5),
                ),
            )

        if "dashboard" in cfg:
            d = cfg["dashboard"]
            self.dashboard = DashboardConfig(
                api_url=d.get("api_url", ""),
                api_key=d.get("api_key", ""),
                websocket_enabled=d.get("websocket_enabled", True),
                websocket_url=d.get("websocket_url", ""),
                sync_interval_seconds=d.get("sync_interval_seconds", 300),
                heartbeat_interval_seconds=d.get("heartbeat_interval_seconds", 60),
                offline_queue_max_size=d.get("offline_queue_max_size", 1000),
            )

        if "system" in cfg:
            s = cfg["system"]
            w = s.get("watchdog", {})
            self.system = SystemConfig(
                watchdog=WatchdogConfig(
                    enabled=w.get("enabled", True),
                    timeout_seconds=w.get("timeout_seconds", 30),
                ),
                auto_restart=s.get("auto_restart", True),
                max_restart_attempts=s.get("max_restart_attempts", 5),
                restart_delay_seconds=s.get("restart_delay_seconds", 10),
                max_memory_mb=s.get("max_memory_mb", 512),
                max_cpu_percent=s.get("max_cpu_percent", 80),
                shutdown_timeout_seconds=s.get("shutdown_timeout_seconds", 10),
            )

        if "logging" in cfg:
            l = cfg["logging"]
            self.logging = LoggingConfig(
                level=l.get("level", "INFO"),
                format=l.get(
                    "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                ),
                console=l.get("console", True),
                file=l.get("file", True),
                file_path=l.get("file_path", "logs/optic-shield.log"),
            )

        if "updates" in cfg:
            u = cfg["updates"]
            self.updates = UpdateConfig(
                enabled=u.get("enabled", False),
                remote=u.get("remote", "origin"),
                branch=u.get("branch", "main"),
                check_interval_seconds=u.get("check_interval_seconds", 0),
                auto_update=u.get("auto_update", False),
                service_name=u.get("service_name", "optic-shield"),
                report_to_portal=u.get("report_to_portal", True),
            )

    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        if os.getenv("OPTIC_API_KEY"):
            self.dashboard.api_key = os.getenv("OPTIC_API_KEY")

        if os.getenv("OPTIC_DASHBOARD_URL"):
            url = os.getenv("OPTIC_DASHBOARD_URL")
            self.dashboard.api_url = f"{url}/api"
            ws_url = url.replace("https://", "wss://").replace("http://", "ws://")
            self.dashboard.websocket_url = f"{ws_url}/ws"

        if os.getenv("OPTIC_DEVICE_ID"):
            self.device.id = os.getenv("OPTIC_DEVICE_ID")

    def _ensure_device_id(self):
        """Ensure device has a unique ID."""
        if not self.device.id:
            id_file = self.config_dir / ".device_id"
            if id_file.exists():
                self.device.id = id_file.read_text().strip()
            else:
                self.device.id = str(uuid.uuid4())[:8]
                id_file.parent.mkdir(parents=True, exist_ok=True)
                id_file.write_text(self.device.id)

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    def get_base_path(self) -> Path:
        """Get base path for the device service."""
        return Path(__file__).parent.parent.parent

    def get_data_path(self) -> Path:
        """Get data directory path."""
        return self.get_base_path() / "data"

    def get_logs_path(self) -> Path:
        """Get logs directory path."""
        return self.get_base_path() / self.storage.logs_path

    def get_platform_info(self) -> Dict[str, Any]:
        """Get platform detection information."""
        try:
            from src.utils.platform_detector import get_detector

            detector = get_detector(self.get_base_path())
            return detector.get_full_report()
        except Exception as e:
            logger.warning(f"Could not get platform info: {e}")
            return {"error": str(e)}
