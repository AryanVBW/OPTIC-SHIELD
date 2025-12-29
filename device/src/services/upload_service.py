"""
Upload service for detection events and images.
Handles reliable transmission to the portal with retry logic.
"""

import logging
import time
import threading
import uuid
import io
import base64
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass

from ..storage.offline_queue import OfflineQueue, DetectionEventPayload
from ..storage.image_store import ImageStore
from .event_logger import EventLogger

logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    """Result of an upload attempt."""
    success: bool
    event_id: str
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class UploadService:
    """
    Service for uploading detection events and images to the portal.
    
    Features:
    - Automatic retry with exponential backoff
    - Offline queue for intermittent connectivity
    - Image compression for bandwidth efficiency
    - Batch uploads for efficiency
    - Event logging for audit trail
    """
    
    def __init__(
        self,
        api_url: str,
        api_key: str,
        device_id: str,
        device_secret: str = "",
        offline_queue: Optional[OfflineQueue] = None,
        image_store: Optional[ImageStore] = None,
        event_logger: Optional[EventLogger] = None,
        upload_interval: int = 30,
        batch_size: int = 5,
        max_image_size_kb: int = 500
    ):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.device_id = device_id
        self.device_secret = device_secret
        self.offline_queue = offline_queue
        self.image_store = image_store
        self.event_logger = event_logger
        self.upload_interval = upload_interval
        self.batch_size = batch_size
        self.max_image_size_kb = max_image_size_kb
        
        self._stop_event = threading.Event()
        self._upload_thread: Optional[threading.Thread] = None
        self._http_client = None
        
        # Stats
        self._upload_count = 0
        self._upload_success = 0
        self._upload_failed = 0
        self._last_upload_time: float = 0
        
        # Device info for metadata
        self._device_info: Dict[str, Any] = {}
        self._location: Dict[str, Any] = {}
        self._cameras: List[Dict[str, Any]] = []
    
    def set_device_info(self, info: Dict[str, Any]):
        """Set device information for metadata."""
        self._device_info = info
    
    def set_location(self, location: Dict[str, Any]):
        """Set device location."""
        self._location = location
    
    def set_cameras(self, cameras: List[Dict[str, Any]]):
        """Set camera information."""
        self._cameras = cameras
    
    def _get_http_client(self):
        """Lazy initialization of HTTP client."""
        if self._http_client is None:
            try:
                import urllib.request
                self._http_client = urllib.request
            except ImportError:
                logger.error("urllib not available")
        return self._http_client
    
    def _generate_signature(self, payload: str, timestamp: int) -> str:
        """Generate HMAC signature for request authentication."""
        if not self.device_secret:
            return ""
        
        import hashlib
        import hmac
        
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
        data: Dict[str, Any],
        timeout: int = 60
    ) -> Optional[Dict[str, Any]]:
        """Make HTTP request to the portal API."""
        import json
        
        http = self._get_http_client()
        if not http:
            return None
        
        url = f"{self.api_url}{endpoint}"
        timestamp = int(time.time())
        payload = json.dumps(data)
        signature = self._generate_signature(payload, timestamp)
        
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "X-Device-ID": self.device_id,
            "X-Timestamp": str(timestamp),
            "X-Signature": signature
        }
        
        try:
            import urllib.request
            import urllib.error
            
            req = urllib.request.Request(
                url,
                data=payload.encode(),
                headers=headers,
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                response_data = response.read().decode()
                return json.loads(response_data) if response_data else {}
                
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error {e.code}: {e.reason}")
            return None
        except urllib.error.URLError as e:
            logger.debug(f"Network error: {e.reason}")
            return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None
    
    def start(self):
        """Start the upload service background thread."""
        if not self.api_url or not self.api_key:
            logger.warning("Upload service not configured, running in offline mode")
            return
        
        self._stop_event.clear()
        
        self._upload_thread = threading.Thread(
            target=self._upload_loop,
            name="UploadService",
            daemon=True
        )
        self._upload_thread.start()
        
        logger.info("Upload service started")
    
    def stop(self):
        """Stop the upload service."""
        self._stop_event.set()
        
        if self._upload_thread and self._upload_thread.is_alive():
            self._upload_thread.join(timeout=10)
        
        logger.info("Upload service stopped")
    
    def _upload_loop(self):
        """Background loop for processing upload queue."""
        while not self._stop_event.is_set():
            try:
                self._process_queue()
            except Exception as e:
                logger.error(f"Upload loop error: {e}")
                if self.event_logger:
                    self.event_logger.log_system_error(
                        str(e), "upload_service"
                    )
            
            self._stop_event.wait(self.upload_interval)
    
    def _process_queue(self):
        """Process pending items from the offline queue."""
        if not self.offline_queue:
            return
        
        items = self.offline_queue.get_pending_items(limit=self.batch_size)
        
        if not items:
            return
        
        # Mark items as in progress
        event_ids = [item['event_id'] for item in items]
        self.offline_queue.mark_in_progress(event_ids)
        
        # Process each item
        successful = []
        for item in items:
            result = self._upload_detection(item)
            
            if result.success:
                successful.append(item['event_id'])
                self._upload_success += 1
                
                if self.event_logger:
                    self.event_logger.log_upload_success(
                        item['event_id'], result.response
                    )
            else:
                self._upload_failed += 1
                self.offline_queue.mark_failed(item['event_id'], result.error or "Unknown error")
                
                if self.event_logger:
                    self.event_logger.log_upload_failed(
                        item['event_id'], result.error or "Unknown error",
                        item.get('attempts', 0) + 1
                    )
            
            self._upload_count += 1
        
        # Mark successful items as completed
        if successful:
            self.offline_queue.mark_completed(successful)
            self._last_upload_time = time.time()
            logger.info(f"Uploaded {len(successful)} detection events to portal")
    
    def _upload_detection(self, item: Dict[str, Any]) -> UploadResult:
        """Upload a single detection event."""
        event_id = item['event_id']
        
        if self.event_logger:
            self.event_logger.log_upload_started(event_id)
        
        # Prepare image data
        image_base64 = None
        if item.get('image_data'):
            image_base64 = base64.b64encode(item['image_data']).decode('utf-8')
        elif item.get('image_path') and self.image_store:
            image_base64 = self.image_store.get_image_base64(
                item['image_path'],
                max_size_kb=self.max_image_size_kb
            )
        
        # Get camera details for this detection
        camera_id = item.get('camera_id', 'unknown')
        camera_details = {"id": camera_id, "name": "Unknown Camera", "model": "Unknown", "type": "unknown"}
        
        # Find matching camera from registered cameras
        for cam in self._cameras:
            if cam.get("id") == camera_id:
                camera_details = cam
                break
        
        # Build payload
        payload = {
            "event_id": event_id,
            "detection_id": item.get('id', 0),
            "device_id": item['device_id'],
            "camera_id": camera_id,
            "camera_details": camera_details,
            "timestamp": item['timestamp'],
            "class_name": item['class_name'],
            "class_id": item['class_id'],
            "confidence": item['confidence'],
            "bbox": item['bbox'],
            "image_base64": image_base64,
            "location": item['location'],
            "metadata": {
                **item.get('metadata', {}),
                "device_info": self._device_info,
                "upload_timestamp": time.time()
            }
        }
        
        # Send to portal
        response = self._make_request("/devices/detections", payload)
        
        if response:
            return UploadResult(
                success=True,
                event_id=event_id,
                response=response
            )
        else:
            return UploadResult(
                success=False,
                event_id=event_id,
                error="Failed to upload to portal"
            )
    
    def queue_detection(
        self,
        detection_id: int,
        class_name: str,
        class_id: int,
        confidence: float,
        bbox: List[int],
        camera_id: str,
        image_path: Optional[str] = None,
        image_data: Optional[bytes] = None,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Queue a detection event for upload.
        
        Returns:
            Event ID for tracking
        """
        event_id = f"det_{self.device_id}_{int(time.time() * 1000)}_{detection_id}"
        
        payload = DetectionEventPayload(
            event_id=event_id,
            device_id=self.device_id,
            camera_id=camera_id,
            timestamp=time.time(),
            class_name=class_name,
            class_id=class_id,
            confidence=confidence,
            bbox=bbox,
            image_path=image_path,
            image_base64=None,  # Will be generated during upload
            location=self._location,
            metadata=metadata or {}
        )
        
        if self.offline_queue:
            self.offline_queue.enqueue(payload, priority=priority, image_data=image_data)
        
        if self.event_logger:
            self.event_logger.log_detection(
                event_id=event_id,
                class_name=class_name,
                confidence=confidence,
                bbox=bbox,
                camera_id=camera_id,
                image_path=image_path,
                location=self._location,
                metadata=metadata
            )
        
        return event_id
    
    def upload_immediate(
        self,
        detection_id: int,
        class_name: str,
        class_id: int,
        confidence: float,
        bbox: List[int],
        camera_id: str,
        image_data: Optional[bytes] = None,
        image_base64: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        """
        Upload a detection immediately (for high-priority alerts).
        Falls back to queue on failure.
        """
        event_id = f"det_{self.device_id}_{int(time.time() * 1000)}_{detection_id}"
        
        if self.event_logger:
            self.event_logger.log_detection(
                event_id=event_id,
                class_name=class_name,
                confidence=confidence,
                bbox=bbox,
                camera_id=camera_id,
                location=self._location,
                metadata=metadata
            )
            self.event_logger.log_upload_started(event_id)
        
        # Prepare image
        if image_data and not image_base64:
            image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Get camera details for this detection
        camera_details = {"id": camera_id, "name": "Unknown Camera", "model": "Unknown", "type": "unknown"}
        
        # Find matching camera from registered cameras
        for cam in self._cameras:
            if cam.get("id") == camera_id:
                camera_details = cam
                break
        
        payload = {
            "event_id": event_id,
            "detection_id": detection_id,
            "device_id": self.device_id,
            "camera_id": camera_id,
            "camera_details": camera_details,
            "timestamp": time.time(),
            "class_name": class_name,
            "class_id": class_id,
            "confidence": confidence,
            "bbox": bbox,
            "image_base64": image_base64,
            "location": self._location,
            "metadata": {
                **(metadata or {}),
                "device_info": self._device_info,
                "upload_timestamp": time.time(),
                "priority": "high"
            }
        }
        
        response = self._make_request("/devices/detections", payload)
        
        if response:
            self._upload_success += 1
            self._upload_count += 1
            self._last_upload_time = time.time()
            
            if self.event_logger:
                self.event_logger.log_upload_success(event_id, response)
            
            logger.info(f"Immediate upload successful: {class_name}")
            return UploadResult(success=True, event_id=event_id, response=response)
        else:
            # Queue for retry
            if self.offline_queue:
                queue_payload = DetectionEventPayload(
                    event_id=event_id,
                    device_id=self.device_id,
                    camera_id=camera_id,
                    timestamp=time.time(),
                    class_name=class_name,
                    class_id=class_id,
                    confidence=confidence,
                    bbox=bbox,
                    image_path=None,
                    image_base64=image_base64,
                    location=self._location,
                    metadata=metadata or {}
                )
                self.offline_queue.enqueue(queue_payload, priority=10, image_data=image_data)
            
            self._upload_failed += 1
            self._upload_count += 1
            
            if self.event_logger:
                self.event_logger.log_upload_failed(event_id, "Network error, queued for retry")
            
            return UploadResult(
                success=False,
                event_id=event_id,
                error="Failed to upload, queued for retry"
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get upload service statistics."""
        queue_stats = self.offline_queue.get_stats() if self.offline_queue else {}
        
        return {
            "api_url": self.api_url,
            "device_id": self.device_id,
            "upload_count": self._upload_count,
            "upload_success": self._upload_success,
            "upload_failed": self._upload_failed,
            "success_rate": round(
                self._upload_success / max(self._upload_count, 1) * 100, 1
            ),
            "last_upload_time": self._last_upload_time,
            "queue": queue_stats
        }
