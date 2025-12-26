"""
Alert service for handling detection notifications.
Supports local GPIO alerts and remote dashboard notifications.
"""

import logging
import time
import threading
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

from ..core.config import Config
from ..api.dashboard_client import DashboardClient, SyncPayload
from ..storage.image_store import ImageStore
from .detection_service import DetectionEvent

logger = logging.getLogger(__name__)


class AlertService:
    """
    Manages alerts for wildlife detections.
    
    Features:
    - Local GPIO alerts (buzzer, LED)
    - Remote dashboard notifications
    - Alert cooldown management
    - Priority-based alert handling
    """
    
    HIGH_PRIORITY_CLASSES = ["bear", "elephant", "wolf"]
    
    def __init__(
        self,
        config: Config,
        dashboard_client: Optional[DashboardClient] = None,
        image_store: Optional[ImageStore] = None
    ):
        self.config = config
        self.dashboard_client = dashboard_client
        self.image_store = image_store
        
        self._gpio_available = False
        self._gpio = None
        self._alert_count = 0
        self._last_alert_time: Dict[str, float] = {}
    
    def initialize(self) -> bool:
        """Initialize alert service."""
        if self.config.alerts.local.gpio_enabled:
            self._init_gpio()
        
        logger.info("Alert service initialized")
        return True
    
    def _init_gpio(self):
        """Initialize GPIO for local alerts."""
        try:
            import RPi.GPIO as GPIO
            self._gpio = GPIO
            self._gpio.setmode(GPIO.BCM)
            self._gpio.setup(
                self.config.alerts.local.gpio_pin,
                GPIO.OUT,
                initial=GPIO.LOW
            )
            self._gpio_available = True
            logger.info(f"GPIO initialized on pin {self.config.alerts.local.gpio_pin}")
        except ImportError:
            logger.debug("RPi.GPIO not available (not running on Raspberry Pi)")
        except Exception as e:
            logger.warning(f"GPIO initialization failed: {e}")
    
    def handle_detection(self, event: DetectionEvent):
        """Handle a detection event and trigger appropriate alerts."""
        if not self.config.alerts.enabled:
            return
        
        for detection in event.detections:
            is_high_priority = detection.class_name in self.HIGH_PRIORITY_CLASSES
            
            if self.config.alerts.local.gpio_enabled and self._gpio_available:
                self._trigger_local_alert(detection.class_name, is_high_priority)
            
            if self.config.alerts.remote.enabled and self.dashboard_client:
                self._send_remote_alert(event, detection, is_high_priority)
            
            self._alert_count += 1
            self._last_alert_time[detection.class_name] = time.time()
    
    def _trigger_local_alert(self, class_name: str, high_priority: bool = False):
        """Trigger local GPIO alert (buzzer/LED)."""
        if not self._gpio_available or not self._gpio:
            return
        
        try:
            pin = self.config.alerts.local.gpio_pin
            duration = self.config.alerts.local.buzzer_duration_ms / 1000.0
            
            if high_priority:
                for _ in range(3):
                    self._gpio.output(pin, self._gpio.HIGH)
                    time.sleep(duration)
                    self._gpio.output(pin, self._gpio.LOW)
                    time.sleep(0.1)
            else:
                self._gpio.output(pin, self._gpio.HIGH)
                time.sleep(duration)
                self._gpio.output(pin, self._gpio.LOW)
            
            logger.debug(f"Local alert triggered for {class_name}")
            
        except Exception as e:
            logger.error(f"Local alert failed: {e}")
    
    def _send_remote_alert(
        self,
        event: DetectionEvent,
        detection,
        high_priority: bool = False
    ):
        """Send alert to remote dashboard."""
        if not self.dashboard_client:
            return
        
        try:
            image_base64 = None
            if self.config.alerts.remote.include_image and self.image_store:
                image_base64 = self._get_compressed_image(event.frame.data)
            
            payload = SyncPayload(
                detection_id=self._alert_count,
                device_id=self.config.device.id,
                timestamp=detection.timestamp,
                class_name=detection.class_name,
                confidence=detection.confidence,
                bbox=list(detection.bbox),
                image_base64=image_base64
            )
            
            if high_priority:
                success = self.dashboard_client.send_detection_immediate(payload)
                if success:
                    logger.info(f"High-priority alert sent: {detection.class_name}")
            else:
                self.dashboard_client.queue_detection(payload)
                logger.debug(f"Alert queued: {detection.class_name}")
                
        except Exception as e:
            logger.error(f"Remote alert failed: {e}")
    
    def _get_compressed_image(self, image_data) -> Optional[str]:
        """Get compressed base64 image for transmission."""
        if not self.image_store:
            return None
        
        try:
            import io
            import base64
            from PIL import Image
            
            img = Image.fromarray(image_data)
            
            max_size = self.config.alerts.remote.image_max_size_kb
            quality = 70
            
            while quality > 10:
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=quality)
                size_kb = buffer.tell() / 1024
                
                if size_kb <= max_size:
                    buffer.seek(0)
                    return base64.b64encode(buffer.read()).decode('utf-8')
                
                quality -= 10
                if quality <= 30:
                    new_size = (img.width // 2, img.height // 2)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    quality = 50
            
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=20)
            buffer.seek(0)
            return base64.b64encode(buffer.read()).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Image compression failed: {e}")
            return None
    
    def cleanup(self):
        """Cleanup GPIO resources."""
        if self._gpio_available and self._gpio:
            try:
                self._gpio.cleanup()
            except Exception:
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get alert service statistics."""
        return {
            "enabled": self.config.alerts.enabled,
            "gpio_available": self._gpio_available,
            "remote_enabled": self.config.alerts.remote.enabled,
            "alert_count": self._alert_count,
            "last_alerts": dict(self._last_alert_time)
        }
