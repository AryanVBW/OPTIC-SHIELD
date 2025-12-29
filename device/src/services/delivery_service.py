"""
Guaranteed delivery service for detection events.
Ensures zero missed detections through robust retry, acknowledgment, and monitoring.
"""

import logging
import time
import threading
import json
import base64
import hashlib
import hmac
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..storage.message_broker import MessageBroker, Message, MessagePriority, CircuitBreaker
from ..storage.image_store import ImageStore

logger = logging.getLogger(__name__)


class DeliveryStatus(Enum):
    """Status of a delivery attempt."""
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"
    CIRCUIT_OPEN = "circuit_open"


@dataclass
class DeliveryResult:
    """Result of a delivery attempt."""
    status: DeliveryStatus
    message_id: str
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    latency_ms: float = 0
    attempt: int = 0


@dataclass
class DeliveryMetrics:
    """Metrics for delivery monitoring."""
    total_attempts: int = 0
    successful: int = 0
    failed: int = 0
    retried: int = 0
    circuit_open_rejections: int = 0
    total_latency_ms: float = 0
    last_success_time: Optional[float] = None
    last_failure_time: Optional[float] = None
    consecutive_failures: int = 0
    
    def record_success(self, latency_ms: float):
        self.total_attempts += 1
        self.successful += 1
        self.total_latency_ms += latency_ms
        self.last_success_time = time.time()
        self.consecutive_failures = 0
    
    def record_failure(self):
        self.total_attempts += 1
        self.failed += 1
        self.last_failure_time = time.time()
        self.consecutive_failures += 1
    
    def record_retry(self):
        self.retried += 1
    
    def get_success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return (self.successful / self.total_attempts) * 100
    
    def get_avg_latency(self) -> float:
        if self.successful == 0:
            return 0.0
        return self.total_latency_ms / self.successful
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_attempts": self.total_attempts,
            "successful": self.successful,
            "failed": self.failed,
            "retried": self.retried,
            "circuit_open_rejections": self.circuit_open_rejections,
            "success_rate": round(self.get_success_rate(), 2),
            "avg_latency_ms": round(self.get_avg_latency(), 2),
            "last_success_time": self.last_success_time,
            "last_failure_time": self.last_failure_time,
            "consecutive_failures": self.consecutive_failures
        }


class HealthChecker:
    """
    Health checker for the delivery service.
    Monitors connectivity and service health.
    """
    
    def __init__(
        self,
        api_url: str,
        api_key: str,
        check_interval: float = 60.0,
        timeout: float = 10.0
    ):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.check_interval = check_interval
        self.timeout = timeout
        
        self._healthy = False
        self._last_check_time: Optional[float] = None
        self._last_check_result: Optional[Dict[str, Any]] = None
        self._check_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def start(self):
        """Start background health checking."""
        self._stop_event.clear()
        self._check_thread = threading.Thread(
            target=self._check_loop,
            name="HealthChecker",
            daemon=True
        )
        self._check_thread.start()
    
    def stop(self):
        """Stop health checking."""
        self._stop_event.set()
        if self._check_thread and self._check_thread.is_alive():
            self._check_thread.join(timeout=5)
    
    def _check_loop(self):
        """Background health check loop."""
        while not self._stop_event.is_set():
            self._perform_check()
            self._stop_event.wait(self.check_interval)
    
    def _perform_check(self):
        """Perform a health check."""
        try:
            import urllib.request
            import urllib.error
            
            url = f"{self.api_url}/api/health"
            req = urllib.request.Request(
                url,
                headers={"X-API-Key": self.api_key},
                method="GET"
            )
            
            start = time.perf_counter()
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                latency = (time.perf_counter() - start) * 1000
                data = json.loads(response.read().decode())
                
                self._healthy = data.get("status") == "ok"
                self._last_check_time = time.time()
                self._last_check_result = {
                    "healthy": self._healthy,
                    "latency_ms": latency,
                    "response": data
                }
                
        except Exception as e:
            self._healthy = False
            self._last_check_time = time.time()
            self._last_check_result = {
                "healthy": False,
                "error": str(e)
            }
    
    @property
    def is_healthy(self) -> bool:
        return self._healthy
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "healthy": self._healthy,
            "last_check_time": self._last_check_time,
            "last_result": self._last_check_result
        }


class GuaranteedDeliveryService:
    """
    Production-grade delivery service with guaranteed message delivery.
    
    Features:
    - Message broker with persistent queue
    - Acknowledgment-based delivery
    - Circuit breaker for fault tolerance
    - Automatic retry with exponential backoff
    - Health monitoring
    - Comprehensive metrics
    - Secure transmission with HMAC signatures
    """
    
    TOPIC_DETECTIONS = "detections"
    TOPIC_HEARTBEAT = "heartbeat"
    TOPIC_ALERTS = "alerts"
    
    def __init__(
        self,
        api_url: str,
        api_key: str,
        device_id: str,
        device_secret: str = "",
        broker_db_path: str = "data/message_broker.db",
        image_store: Optional[ImageStore] = None,
        delivery_interval: float = 5.0,
        batch_size: int = 10,
        max_image_size_kb: int = 500,
        request_timeout: int = 60
    ):
        self.api_url = api_url.rstrip('/') if api_url else ""
        self.api_key = api_key
        self.device_id = device_id
        self.device_secret = device_secret
        self.image_store = image_store
        self.delivery_interval = delivery_interval
        self.batch_size = batch_size
        self.max_image_size_kb = max_image_size_kb
        self.request_timeout = request_timeout
        
        # Initialize message broker
        self.broker = MessageBroker(
            db_path=broker_db_path,
            max_queue_size=50000,
            max_in_flight=100,
            visibility_timeout=300.0
        )
        
        # Health checker
        self.health_checker = HealthChecker(
            api_url=api_url,
            api_key=api_key
        ) if api_url else None
        
        # Metrics
        self.metrics = DeliveryMetrics()
        
        # Device info
        self._device_info: Dict[str, Any] = {}
        self._location: Dict[str, Any] = {}
        self._cameras: List[Dict[str, Any]] = []
        
        # Threading
        self._stop_event = threading.Event()
        self._delivery_thread: Optional[threading.Thread] = None
        self._cleanup_thread: Optional[threading.Thread] = None
        
        # Callbacks for events
        self._on_delivery_success: List[Callable] = []
        self._on_delivery_failure: List[Callable] = []
    
    def initialize(self) -> bool:
        """Initialize the delivery service."""
        try:
            if not self.broker.initialize():
                logger.error("Failed to initialize message broker")
                return False
            
            logger.info("Guaranteed delivery service initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize delivery service: {e}")
            return False
    
    def set_device_info(self, info: Dict[str, Any]):
        """Set device information for metadata."""
        self._device_info = info
    
    def set_location(self, location: Dict[str, Any]):
        """Set device location."""
        self._location = location
    
    def set_cameras(self, cameras: List[Dict[str, Any]]):
        """Set camera information."""
        self._cameras = cameras
    
    def add_success_callback(self, callback: Callable):
        """Add callback for successful deliveries."""
        self._on_delivery_success.append(callback)
    
    def add_failure_callback(self, callback: Callable):
        """Add callback for failed deliveries."""
        self._on_delivery_failure.append(callback)
    
    def start(self):
        """Start the delivery service."""
        if not self.api_url or not self.api_key:
            logger.warning("Delivery service not configured, running in offline mode")
            return
        
        self._stop_event.clear()
        
        # Start health checker
        if self.health_checker:
            self.health_checker.start()
        
        # Start delivery thread
        self._delivery_thread = threading.Thread(
            target=self._delivery_loop,
            name="DeliveryService",
            daemon=True
        )
        self._delivery_thread.start()
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            name="DeliveryCleanup",
            daemon=True
        )
        self._cleanup_thread.start()
        
        logger.info("Guaranteed delivery service started")
    
    def stop(self):
        """Stop the delivery service."""
        self._stop_event.set()
        
        if self.health_checker:
            self.health_checker.stop()
        
        if self._delivery_thread and self._delivery_thread.is_alive():
            self._delivery_thread.join(timeout=10)
        
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        
        logger.info("Guaranteed delivery service stopped")
    
    def _delivery_loop(self):
        """Main delivery loop."""
        while not self._stop_event.is_set():
            try:
                self._process_pending_messages()
            except Exception as e:
                logger.error(f"Delivery loop error: {e}")
            
            self._stop_event.wait(self.delivery_interval)
    
    def _cleanup_loop(self):
        """Periodic cleanup loop."""
        while not self._stop_event.is_set():
            try:
                self.broker.cleanup_expired()
                self.broker.cleanup_old_ack_logs(days=7)
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
            
            # Run cleanup every hour
            self._stop_event.wait(3600)
    
    def _process_pending_messages(self):
        """Process pending messages from the broker."""
        # Process detections
        messages = self.broker.consume(
            topic=self.TOPIC_DETECTIONS,
            batch_size=self.batch_size
        )
        
        for message in messages:
            result = self._deliver_detection(message)
            self._handle_delivery_result(message, result)
    
    def _deliver_detection(self, message: Message) -> DeliveryResult:
        """Deliver a detection message to the portal."""
        start_time = time.perf_counter()
        
        try:
            payload = message.payload
            
            # Prepare image if available
            image_base64 = payload.get("image_base64")
            if not image_base64 and payload.get("image_path") and self.image_store:
                image_base64 = self.image_store.get_image_base64(
                    payload["image_path"],
                    max_size_kb=self.max_image_size_kb
                )
            
            # Get camera details for this detection
            camera_id = payload.get("camera_id", "unknown")
            camera_details = {"id": camera_id, "name": "Unknown Camera", "model": "Unknown", "type": "unknown"}
            
            # Find matching camera from registered cameras
            for cam in self._cameras:
                if cam.get("id") == camera_id:
                    camera_details = cam
                    break
            
            # Build request payload
            request_payload = {
                "event_id": payload.get("detection_id", message.id),
                "device_id": self.device_id,
                "camera_id": camera_id,
                "camera_details": camera_details,
                "timestamp": payload.get("timestamp", time.time()),
                "class_name": payload.get("class_name"),
                "class_id": payload.get("class_id"),
                "confidence": payload.get("confidence"),
                "bbox": payload.get("bbox"),
                "image_base64": image_base64,
                "location": payload.get("location", self._location),
                "metadata": {
                    **payload.get("metadata", {}),
                    "device_info": self._device_info,
                    "delivery_timestamp": time.time(),
                    "attempt": message.attempts + 1,
                    "message_checksum": message.checksum
                }
            }
            
            # Send request
            response = self._make_request("/devices/detections", request_payload)
            
            latency = (time.perf_counter() - start_time) * 1000
            
            if response and response.get("success"):
                return DeliveryResult(
                    status=DeliveryStatus.SUCCESS,
                    message_id=message.id,
                    response=response,
                    latency_ms=latency,
                    attempt=message.attempts + 1
                )
            else:
                error = response.get("error", "Unknown error") if response else "No response"
                return DeliveryResult(
                    status=DeliveryStatus.FAILED,
                    message_id=message.id,
                    error=error,
                    latency_ms=latency,
                    attempt=message.attempts + 1
                )
                
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            return DeliveryResult(
                status=DeliveryStatus.FAILED,
                message_id=message.id,
                error=str(e),
                latency_ms=latency,
                attempt=message.attempts + 1
            )
    
    def _handle_delivery_result(self, message: Message, result: DeliveryResult):
        """Handle the result of a delivery attempt."""
        if result.status == DeliveryStatus.SUCCESS:
            # Acknowledge the message
            self.broker.acknowledge(
                message_id=message.id,
                ack_token=message.ack_token,
                response=result.response
            )
            
            self.metrics.record_success(result.latency_ms)
            
            # Notify callbacks
            for callback in self._on_delivery_success:
                try:
                    callback(message.id, result)
                except Exception as e:
                    logger.error(f"Success callback error: {e}")
            
            logger.info(f"Detection delivered: {message.id} (attempt {result.attempt}, {result.latency_ms:.0f}ms)")
            
        else:
            # Negative acknowledge for retry
            self.broker.negative_acknowledge(
                message_id=message.id,
                ack_token=message.ack_token,
                error=result.error or "Unknown error",
                retry=True
            )
            
            self.metrics.record_failure()
            self.metrics.record_retry()
            
            # Notify callbacks
            for callback in self._on_delivery_failure:
                try:
                    callback(message.id, result)
                except Exception as e:
                    logger.error(f"Failure callback error: {e}")
            
            logger.warning(f"Detection delivery failed: {message.id} - {result.error}")
    
    def _generate_signature(self, payload: str, timestamp: int) -> str:
        """Generate HMAC signature for request authentication."""
        if not self.device_secret:
            return ""
        
        message = f"{timestamp}.{payload}"
        signature = hmac.new(
            self.device_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_request(
        self,
        endpoint: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request to the portal API."""
        import urllib.request
        import urllib.error
        
        url = f"{self.api_url}{endpoint}"
        timestamp = int(time.time())
        payload = json.dumps(data)
        signature = self._generate_signature(payload, timestamp)
        
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "X-Device-ID": self.device_id,
            "X-Timestamp": str(timestamp),
            "X-Signature": signature,
            "X-Message-ID": data.get("event_id", "")
        }
        
        try:
            req = urllib.request.Request(
                url,
                data=payload.encode(),
                headers=headers,
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=self.request_timeout) as response:
                response_data = response.read().decode()
                result = json.loads(response_data) if response_data else {}
                
                # Check for acknowledgment
                if "ack_id" in result:
                    logger.debug(f"Received server ack: {result['ack_id']}")
                
                return {"success": True, **result}
                
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error {e.code}: {e.reason}")
            return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            logger.debug(f"Network error: {e.reason}")
            return {"success": False, "error": f"Network error: {e.reason}"}
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {"success": False, "error": str(e)}
    
    def queue_detection(
        self,
        detection_id: int,
        class_name: str,
        class_id: int,
        confidence: float,
        bbox: List[int],
        camera_id: str,
        timestamp: Optional[float] = None,
        image_path: Optional[str] = None,
        image_data: Optional[bytes] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Queue a detection event for guaranteed delivery.
        
        Returns:
            Message ID if queued successfully
        """
        event_id = f"det_{self.device_id}_{int(time.time() * 1000)}_{detection_id}"
        
        # Prepare image
        image_base64 = None
        if image_data:
            image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        payload = {
            "detection_id": detection_id,
            "class_name": class_name,
            "class_id": class_id,
            "confidence": confidence,
            "bbox": bbox,
            "camera_id": camera_id,
            "timestamp": timestamp or time.time(),
            "image_path": image_path,
            "image_base64": image_base64,
            "location": self._location,
            "metadata": metadata or {}
        }
        
        message_id = self.broker.publish(
            topic=self.TOPIC_DETECTIONS,
            payload=payload,
            priority=priority,
            idempotency_key=event_id,
            metadata={
                "device_id": self.device_id,
                "class_name": class_name,
                "queued_at": time.time()
            }
        )
        
        if message_id:
            logger.debug(f"Queued detection: {message_id} ({class_name})")
        
        return message_id
    
    def queue_high_priority_detection(
        self,
        detection_id: int,
        class_name: str,
        class_id: int,
        confidence: float,
        bbox: List[int],
        camera_id: str,
        image_data: Optional[bytes] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Queue a high-priority detection (dangerous animals)."""
        return self.queue_detection(
            detection_id=detection_id,
            class_name=class_name,
            class_id=class_id,
            confidence=confidence,
            bbox=bbox,
            camera_id=camera_id,
            image_data=image_data,
            priority=MessagePriority.CRITICAL,
            metadata={
                **(metadata or {}),
                "priority": "critical",
                "immediate": True
            }
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get delivery service statistics."""
        return {
            "api_url": self.api_url,
            "device_id": self.device_id,
            "metrics": self.metrics.to_dict(),
            "broker": self.broker.get_stats(),
            "health": self.health_checker.get_status() if self.health_checker else None
        }
    
    def get_pending_count(self) -> int:
        """Get count of pending messages."""
        stats = self.broker.get_stats()
        return stats.get("queue_pending", 0)
    
    def get_dead_letter_count(self) -> int:
        """Get count of dead letter messages."""
        stats = self.broker.get_stats()
        return stats.get("dead_letter_queue", 0)
    
    def replay_failed_messages(self, limit: int = 10) -> int:
        """Replay messages from dead letter queue."""
        dlq_messages = self.broker.get_dead_letter_messages(
            topic=self.TOPIC_DETECTIONS,
            limit=limit
        )
        
        replayed = 0
        for msg in dlq_messages:
            if self.broker.replay_dead_letter(msg["id"]):
                replayed += 1
        
        if replayed > 0:
            logger.info(f"Replayed {replayed} messages from dead letter queue")
        
        return replayed
