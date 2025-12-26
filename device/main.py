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

from src.core.config import Config
from src.services.detection_service import DetectionService, ServiceState
from src.services.alert_service import AlertService
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
        self.system_monitor: SystemMonitor = None
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
            
            if self.config.dashboard.api_url and self.config.dashboard.api_key:
                device_secret = os.getenv("OPTIC_DEVICE_SECRET", "")
                self.dashboard_client = DashboardClient(
                    api_url=self.config.dashboard.api_url,
                    api_key=self.config.dashboard.api_key,
                    device_id=self.config.device.id,
                    device_secret=device_secret,
                    sync_interval=self.config.dashboard.sync_interval_seconds,
                    heartbeat_interval=self.config.dashboard.heartbeat_interval_seconds,
                    offline_queue_max_size=self.config.dashboard.offline_queue_max_size
                )
            
            self.detection_service = DetectionService(self.config)
            
            if not self.detection_service.initialize():
                logger.error("Detection service initialization failed")
                return False
            
            self.alert_service = AlertService(
                config=self.config,
                dashboard_client=self.dashboard_client,
                image_store=self.detection_service.image_store
            )
            self.alert_service.initialize()
            
            self.detection_service.add_detection_callback(
                self.alert_service.handle_detection
            )
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            return False
    
    def start(self):
        """Start all services."""
        logger.info("Starting OPTIC-SHIELD services...")
        
        self.system_monitor.start()
        
        if self.dashboard_client:
            self.dashboard_client.start()
            
            self.dashboard_client.register_device({
                "name": self.config.device.name,
                "location": {
                    "name": self.config.device.location_name,
                    "latitude": self.config.device.latitude,
                    "longitude": self.config.device.longitude
                },
                "environment": self.config.environment,
                "version": "1.0.0"
            })
        
        self.detection_service.start()
        
        logger.info("All services started")
    
    def stop(self):
        """Stop all services gracefully."""
        logger.info("Stopping OPTIC-SHIELD services...")
        
        if self.detection_service:
            self.detection_service.stop()
        
        if self.alert_service:
            self.alert_service.cleanup()
        
        if self.dashboard_client:
            self.dashboard_client.stop()
        
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
            "restart_count": self._restart_count
        }
        
        if self.detection_service:
            stats["detection_service"] = self.detection_service.get_stats()
        
        if self.alert_service:
            stats["alert_service"] = self.alert_service.get_stats()
        
        if self.dashboard_client:
            stats["dashboard_client"] = self.dashboard_client.get_stats()
        
        if self.system_monitor:
            stats["system"] = self.system_monitor.get_stats_dict()
        
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
