#!/usr/bin/env python3
"""
OPTIC-SHIELD - Wildlife Detection Service for Raspberry Pi 5

Main entry point for the detection service.
Designed for continuous 24/7 operation with robust error handling.
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Early dependency check before importing other modules
from src.utils.dependency_checker import check_and_install_dependencies

# Check and auto-install dependencies before proceeding
if not check_and_install_dependencies(auto_install=True):
    print("ERROR: Failed to ensure all dependencies. Please install manually.")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

from src.core.config import Config
from src.services.detection_service import DetectionService, ServiceState
from src.services.alert_service import AlertService
from src.services.upload_service import UploadService
from src.services.event_logger import EventLogger
from src.services.delivery_service import GuaranteedDeliveryService
from src.services.location_service import LocationService
from src.services.health_monitor import HealthMonitor, HealthStatus, HealthCheck
from src.services.update_service import UpdateService, UpdateSource
from src.storage.offline_queue import OfflineQueue
from src.api.dashboard_client import DashboardClient
from src.utils.logging_setup import setup_logging
from src.utils.system_monitor import SystemMonitor

logger = logging.getLogger(__name__)


class OpticShield:
    """
    Main application class for OPTIC-SHIELD.
    Orchestrates all services and handles lifecycle management.
    """
    
    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir) if config_dir else None
        self.config: Config = None
        self.detection_service: DetectionService = None
        self.alert_service: AlertService = None
        self.dashboard_client: DashboardClient = None
        self.upload_service: UploadService = None
        self.event_logger: EventLogger = None
        self.offline_queue: OfflineQueue = None
        self.system_monitor: SystemMonitor = None
        self.delivery_service: GuaranteedDeliveryService = None
        self.location_service: LocationService = None
        self.health_monitor: HealthMonitor = None
        self.update_service: UpdateService = None
        self._restart_count = 0
    
    def initialize(self) -> bool:
        """Initialize all components."""
        try:
            self.config = Config.get_instance(self.config_dir)
            
            setup_logging(self.config)
            
            logger.info("=" * 60)
            logger.info("OPTIC-SHIELD Wildlife Detection System")
            logger.info(f"Environment: {self.config.environment}")
            logger.info(f"Device ID: {self.config.device.id}")
            logger.info(f"Device Name: {self.config.device.name}")
            logger.info("=" * 60)
            
            self.system_monitor = SystemMonitor(
                max_memory_mb=self.config.system.max_memory_mb,
                max_cpu_percent=self.config.system.max_cpu_percent,
                check_interval=30
            )
            
            # Initialize event logger for audit trail
            base_path = self.config.get_base_path()
            self.event_logger = EventLogger(
                log_dir=str(base_path / "data" / "event_logs"),
                device_id=self.config.device.id,
                retention_days=self.config.storage.logs_retention_days
            )
            self.event_logger.initialize()
            
            # Initialize offline queue for reliable uploads
            self.offline_queue = OfflineQueue(
                db_path=str(base_path / "data" / "offline_queue.db"),
                max_queue_size=self.config.dashboard.offline_queue_max_size
            )
            self.offline_queue.initialize()
            
            # Initialize location service for GPS/location tracking
            self.location_service = LocationService(
                default_latitude=self.config.device.latitude,
                default_longitude=self.config.device.longitude,
                default_location_name=self.config.device.location_name,
                gps_port=os.getenv("OPTIC_GPS_PORT"),  # Optional GPS serial port
                cache_file=str(base_path / "data" / "location_cache.json")
            )
            self.location_service.initialize()
            
            # Initialize health monitor for system health tracking
            self.health_monitor = HealthMonitor(
                check_interval=30.0,
                alert_cooldown=300.0
            )
            self.health_monitor.set_device_id(self.config.device.id)
            
            if self.config.dashboard.api_url and self.config.dashboard.api_key:
                device_secret = os.getenv("OPTIC_DEVICE_SECRET", "")
                self.dashboard_client = DashboardClient(
                    api_url=self.config.dashboard.api_url,
                    api_key=self.config.dashboard.api_key,
                    device_id=self.config.device.id,
                    device_secret=device_secret,
                    sync_interval=self.config.dashboard.sync_interval_seconds,
                    heartbeat_interval=self.config.dashboard.heartbeat_interval_seconds,
                    offline_queue_max_size=self.config.dashboard.offline_queue_max_size,
                    environment=self.config.environment
                )
            
            self.detection_service = DetectionService(self.config)
            
            if not self.detection_service.initialize():
                logger.error("Detection service initialization failed")
                return False
            
            # Initialize guaranteed delivery service (production-grade message broker)
            device_secret = os.getenv("OPTIC_DEVICE_SECRET", "")
            self.delivery_service = GuaranteedDeliveryService(
                api_url=self.config.dashboard.api_url,
                api_key=self.config.dashboard.api_key,
                device_id=self.config.device.id,
                device_secret=device_secret,
                broker_db_path=str(base_path / "data" / "message_broker.db"),
                image_store=self.detection_service.image_store,
                delivery_interval=5.0,
                batch_size=10,
                max_image_size_kb=self.config.alerts.remote.image_max_size_kb
            )
            self.delivery_service.initialize()
            
            # Set device metadata for delivery service
            self.delivery_service.set_device_info({
                "name": self.config.device.name,
                "environment": self.config.environment,
                "version": "2.0.0",
                "hardware_model": "Raspberry Pi 5"
            })
            self.delivery_service.set_location(self.location_service.get_location_dict())
            
            # Initialize legacy upload service (for backward compatibility)
            self.upload_service = UploadService(
                api_url=self.config.dashboard.api_url,
                api_key=self.config.dashboard.api_key,
                device_id=self.config.device.id,
                device_secret=device_secret,
                offline_queue=self.offline_queue,
                image_store=self.detection_service.image_store,
                event_logger=self.event_logger,
                upload_interval=30,
                batch_size=5,
                max_image_size_kb=self.config.alerts.remote.image_max_size_kb
            )
            
            # Set device metadata for uploads
            self.upload_service.set_device_info({
                "name": self.config.device.name,
                "environment": self.config.environment,
                "version": "2.0.0",
                "hardware_model": "Raspberry Pi 5"
            })
            self.upload_service.set_location(self.location_service.get_location_dict())
            
            self.alert_service = AlertService(
                config=self.config,
                dashboard_client=self.dashboard_client,
                image_store=self.detection_service.image_store,
                upload_service=self.upload_service,
                event_logger=self.event_logger
            )
            self.alert_service.initialize()
            
            # Register health checks for all components
            self._register_health_checks()
            
            self.detection_service.add_detection_callback(
                self.alert_service.handle_detection
            )
            
            # Add callback to queue detections via guaranteed delivery
            self.detection_service.add_detection_callback(
                self._handle_detection_for_delivery
            )
            
            # Initialize update service (only if enabled in config)
            # Updates are portal-triggered only when disabled
            if self.config.updates.enabled:
                device_secret = os.getenv("OPTIC_DEVICE_SECRET", "")
                self.update_service = UpdateService(
                    repo_path=str(Path(__file__).parent.parent),  # Root of the repo
                    remote_name=self.config.updates.remote,
                    branch=self.config.updates.branch,
                    check_interval=float(self.config.updates.check_interval_seconds),
                    auto_update=self.config.updates.auto_update,
                    service_name=self.config.updates.service_name,
                    api_url=self.config.dashboard.api_url,
                    api_key=self.config.dashboard.api_key,
                    device_id=self.config.device.id,
                    device_secret=device_secret
                )
                self.update_service.initialize()
                
                # Register update callbacks
                self.update_service.add_update_available_callback(
                    lambda info: logger.info(f"Update available: {info.commits_behind} commits behind")
                )
                self.update_service.add_update_complete_callback(
                    lambda result: logger.info(f"Update complete: {result.message}")
                )
            else:
                logger.info("Automatic updates disabled - updates will be triggered from portal only")
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            return False
    
    def _register_health_checks(self):
        """Register health checks for all components."""
        if not self.health_monitor:
            return
        
        # Camera health check
        if self.detection_service and self.detection_service.camera:
            self.health_monitor.register_health_check(
                "camera",
                self.health_monitor.create_camera_health_check(self.detection_service.camera)
            )
        
        # Detector health check
        if self.detection_service and self.detection_service.detector:
            self.health_monitor.register_health_check(
                "detector",
                self.health_monitor.create_detector_health_check(self.detection_service.detector)
            )
        
        # Delivery service health check
        if self.delivery_service:
            self.health_monitor.register_health_check(
                "delivery",
                self.health_monitor.create_delivery_health_check(self.delivery_service)
            )
        
        # Register self-healing actions
        if self.detection_service:
            self.health_monitor.self_healer.register_recovery_action(
                "camera",
                lambda: self._recover_camera()
            )
            self.health_monitor.self_healer.register_recovery_action(
                "detector",
                lambda: self._recover_detector()
            )
    
    def _recover_camera(self) -> bool:
        """Attempt to recover the camera."""
        try:
            if self.detection_service and self.detection_service.camera:
                self.detection_service.camera.stop()
                time.sleep(2)
                return self.detection_service.camera.initialize()
        except Exception as e:
            logger.error(f"Camera recovery failed: {e}")
        return False
    
    def _recover_detector(self) -> bool:
        """Attempt to recover the detector."""
        try:
            if self.detection_service and self.detection_service.detector:
                self.detection_service.detector.unload()
                time.sleep(1)
                return self.detection_service.detector.load_model()
        except Exception as e:
            logger.error(f"Detector recovery failed: {e}")
        return False
    
    def _handle_detection_for_delivery(self, event):
        """Handle detection event for guaranteed delivery."""
        if not self.delivery_service:
            return
        
        from src.storage.message_broker import MessagePriority
        
        for detection in event.detections:
            # Determine priority based on animal type
            high_priority_animals = ["tiger", "leopard", "lion", "bear", "elephant"]
            priority = MessagePriority.CRITICAL if detection.class_name.lower() in high_priority_animals else MessagePriority.NORMAL
            
            # Get image data if available
            image_data = None
            if hasattr(event.frame, 'data') and event.frame.data is not None:
                try:
                    import cv2
                    _, buffer = cv2.imencode('.jpg', event.frame.data, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    image_data = buffer.tobytes()
                except Exception:
                    pass
            
            # Queue for guaranteed delivery
            self.delivery_service.queue_detection(
                detection_id=self._get_next_detection_id(),
                class_name=detection.class_name,
                class_id=detection.class_id,
                confidence=detection.confidence,
                bbox=list(detection.bbox),
                camera_id=f"cam-{self.config.device.id}-0",
                timestamp=detection.timestamp,
                image_data=image_data,
                priority=priority,
                metadata={
                    "processing_time_ms": event.processing_time_ms,
                    "frame_timestamp": event.timestamp
                }
            )
    
    def _get_next_detection_id(self) -> int:
        """Get next detection ID."""
        if not hasattr(self, '_detection_counter'):
            self._detection_counter = 0
        self._detection_counter += 1
        return self._detection_counter
    
    def start(self):
        """Start all services."""
        logger.info("Starting OPTIC-SHIELD services...")
        
        self.system_monitor.start()
        
        # Start location service
        if self.location_service:
            self.location_service.start()
        
        # Start health monitor
        if self.health_monitor:
            self.health_monitor.start()
        
        if self.dashboard_client:
            self.dashboard_client.set_system_monitor(self.system_monitor)
            
            device_info = {
                "name": self.config.device.name,
                "location": self.location_service.get_location_dict() if self.location_service else {
                    "name": self.config.device.location_name,
                    "latitude": self.config.device.latitude,
                    "longitude": self.config.device.longitude
                },
                "environment": self.config.environment,
                "version": "2.0.0",
                "hardware_model": "Raspberry Pi 5",
                "tags": ["wildlife", "detection", self.config.environment]
            }
            self.dashboard_client.set_device_info(device_info)
            
            cameras = self._get_camera_info()
            self.dashboard_client.set_cameras(cameras)
            
            self.dashboard_client.start()
            self.dashboard_client.register_device(device_info)
        
        # Start guaranteed delivery service
        if self.delivery_service:
            cameras = self._get_camera_info()
            self.delivery_service.set_cameras(cameras)
            self.delivery_service.start()
        
        # Start legacy upload service for backward compatibility
        if self.upload_service:
            cameras = self._get_camera_info()
            self.upload_service.set_cameras(cameras)
            self.upload_service.start()
        
        # Start update service
        if self.update_service:
            self.update_service.start()
        
        self.detection_service.start()
        
        logger.info("All services started")
    
    def _get_camera_info(self) -> list:
        """Get camera information for telemetry."""
        cameras = []
        if self.config.camera.enabled and self.detection_service and self.detection_service.camera:
            # Get actual camera info from the camera manager
            camera_info = self.detection_service.camera.get_camera_info()
            cameras.append({
                "id": f"cam-{self.config.device.id}-0",
                "name": camera_info.get("name", "Unknown Camera"),
                "model": camera_info.get("model", "Unknown"),
                "type": camera_info.get("type", "unknown"),
                "device_path": camera_info.get("device_path", "unknown"),
                "resolution": camera_info.get("resolution", f"{self.config.camera.width}x{self.config.camera.height}"),
                "fps": camera_info.get("fps", self.config.camera.fps),
                "status": camera_info.get("status", "unknown")
            })
        elif self.config.camera.enabled:
            # Fallback if camera not initialized yet
            cameras.append({
                "id": f"cam-{self.config.device.id}-0",
                "name": "Unknown Camera",
                "model": "Unknown",
                "type": "unknown",
                "device_path": "unknown",
                "resolution": f"{self.config.camera.width}x{self.config.camera.height}",
                "fps": self.config.camera.fps,
                "status": "unknown"
            })
        return cameras
    
    def stop(self):
        """Stop all services gracefully."""
        logger.info("Stopping OPTIC-SHIELD services...")
        
        if self.detection_service:
            self.detection_service.stop()
        
        if self.alert_service:
            self.alert_service.cleanup()
        
        if self.delivery_service:
            self.delivery_service.stop()
        
        if self.upload_service:
            self.upload_service.stop()
        
        if self.dashboard_client:
            self.dashboard_client.stop()
        
        if self.update_service:
            self.update_service.stop()
        
        if self.health_monitor:
            self.health_monitor.stop()
        
        if self.location_service:
            self.location_service.stop()
        
        if self.system_monitor:
            self.system_monitor.stop()
        
        logger.info("All services stopped")
    
    def run(self):
        """Run the application with auto-restart capability."""
        while True:
            try:
                if not self.initialize():
                    logger.error("Initialization failed, retrying in 10 seconds...")
                    time.sleep(10)
                    self._restart_count += 1
                    
                    if self._restart_count >= self.config.system.max_restart_attempts:
                        logger.critical("Max restart attempts reached, exiting")
                        sys.exit(1)
                    continue
                
                self.start()
                
                while self.detection_service.state == ServiceState.RUNNING:
                    time.sleep(1)
                    
                    stats = self.get_stats()
                    if stats.get("detection_service", {}).get("error_count", 0) > 100:
                        logger.warning("High error count, triggering restart")
                        break
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Runtime error: {e}", exc_info=True)
                self._restart_count += 1
                
                if not self.config.system.auto_restart:
                    break
                
                if self._restart_count >= self.config.system.max_restart_attempts:
                    logger.critical("Max restart attempts reached, exiting")
                    break
                
                logger.info(f"Restarting in {self.config.system.restart_delay_seconds} seconds...")
                time.sleep(self.config.system.restart_delay_seconds)
            finally:
                self.stop()
        
        logger.info("OPTIC-SHIELD shutdown complete")
    
    def get_stats(self) -> dict:
        """Get comprehensive system statistics."""
        stats = {
            "device_id": self.config.device.id if self.config else None,
            "device_name": self.config.device.name if self.config else None,
            "environment": self.config.environment if self.config else None,
            "restart_count": self._restart_count,
            "version": "2.0.0"
        }
        
        if self.detection_service:
            stats["detection_service"] = self.detection_service.get_stats()
        
        if self.alert_service:
            stats["alert_service"] = self.alert_service.get_stats()
        
        if self.delivery_service:
            stats["delivery_service"] = self.delivery_service.get_stats()
        
        if self.upload_service:
            stats["upload_service"] = self.upload_service.get_stats()
        
        if self.offline_queue:
            stats["offline_queue"] = self.offline_queue.get_stats()
        
        if self.event_logger:
            stats["event_logger"] = self.event_logger.get_stats()
        
        if self.dashboard_client:
            stats["dashboard_client"] = self.dashboard_client.get_stats()
        
        if self.health_monitor:
            stats["health"] = self.health_monitor.get_health_report()
        
        if self.location_service:
            stats["location"] = self.location_service.get_stats()
        
        if self.system_monitor:
            stats["system"] = self.system_monitor.get_stats_dict()
        
        if self.update_service:
            stats["update_service"] = self.update_service.get_stats()
        
        return stats


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="OPTIC-SHIELD Wildlife Detection System"
    )
    parser.add_argument(
        "--config-dir",
        type=str,
        default=None,
        help="Path to configuration directory"
    )
    parser.add_argument(
        "--env",
        type=str,
        choices=["development", "production"],
        default=None,
        help="Environment (overrides OPTIC_ENV)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    if args.env:
        os.environ["OPTIC_ENV"] = args.env
    
    if args.debug:
        os.environ["OPTIC_DEBUG"] = "1"
    
    app = OpticShield(config_dir=args.config_dir)
    app.run()


if __name__ == "__main__":
    main()
