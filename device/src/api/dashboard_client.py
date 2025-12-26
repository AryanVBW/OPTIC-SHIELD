"""
API client for communicating with the Vercel dashboard.
Handles authentication, sync, and offline queue management.
"""

import logging
import time
import json
import threading
import hashlib
import hmac
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from queue import Queue, Empty
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class SyncPayload:
    """Payload for syncing detection to dashboard."""
    detection_id: int
    device_id: str
    timestamp: float
    class_name: str
    confidence: float
    bbox: List[int]
    image_base64: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detection_id": self.detection_id,
            "device_id": self.device_id,
            "timestamp": self.timestamp,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "image_base64": self.image_base64
        }


class DashboardClient:
    """
    Client for communicating with the Vercel-hosted dashboard.
    
    Features:
    - Secure authentication with API key and device secret
    - Automatic retry with exponential backoff
    - Offline queue for when network is unavailable
    - Heartbeat for device status monitoring
    """
    
    def __init__(
        self,
        api_url: str,
        api_key: str,
        device_id: str,
        device_secret: str = "",
        sync_interval: int = 300,
        heartbeat_interval: int = 60,
        offline_queue_max_size: int = 1000
    ):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.device_id = device_id
        self.device_secret = device_secret
        self.sync_interval = sync_interval
        self.heartbeat_interval = heartbeat_interval
        
        self.state = ConnectionState.DISCONNECTED
        self._offline_queue: Queue = Queue(maxsize=offline_queue_max_size)
        self._stop_event = threading.Event()
        self._sync_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        
        self._last_sync_time: float = 0
        self._last_heartbeat_time: float = 0
        self._sync_success_count = 0
        self._sync_failure_count = 0
        
        self._http_client = None
    
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
        method: str = "POST",
        data: Optional[Dict] = None,
        timeout: int = 30
    ) -> Optional[Dict]:
        """Make an HTTP request to the dashboard API."""
        http = self._get_http_client()
        if not http:
            return None
        
        url = f"{self.api_url}{endpoint}"
        timestamp = int(time.time())
        
        payload = json.dumps(data) if data else ""
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
                data=payload.encode() if payload else None,
                headers=headers,
                method=method
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
        """Start background sync and heartbeat threads."""
        if not self.api_url or not self.api_key:
            logger.warning("Dashboard API not configured, running in offline mode")
            return
        
        self._stop_event.clear()
        
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="DashboardHeartbeat",
            daemon=True
        )
        self._heartbeat_thread.start()
        
        self._sync_thread = threading.Thread(
            target=self._sync_loop,
            name="DashboardSync",
            daemon=True
        )
        self._sync_thread.start()
        
        logger.info("Dashboard client started")
    
    def stop(self):
        """Stop background threads."""
        self._stop_event.set()
        
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5)
        
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5)
        
        self.state = ConnectionState.DISCONNECTED
        logger.info("Dashboard client stopped")
    
    def queue_detection(self, payload: SyncPayload) -> bool:
        """Queue a detection for sync to dashboard."""
        try:
            self._offline_queue.put_nowait(payload)
            return True
        except:
            logger.warning("Offline queue full, dropping detection")
            return False
    
    def send_detection_immediate(self, payload: SyncPayload) -> bool:
        """Send a detection immediately (for high-priority alerts)."""
        response = self._make_request(
            "/devices/detections",
            data=payload.to_dict()
        )
        
        if response:
            self._sync_success_count += 1
            return True
        else:
            self.queue_detection(payload)
            self._sync_failure_count += 1
            return False
    
    def _heartbeat_loop(self):
        """Background loop for sending heartbeats."""
        while not self._stop_event.is_set():
            try:
                self._send_heartbeat()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            
            self._stop_event.wait(self.heartbeat_interval)
    
    def _send_heartbeat(self):
        """Send device heartbeat to dashboard."""
        data = {
            "device_id": self.device_id,
            "timestamp": time.time(),
            "status": "online",
            "stats": self.get_stats()
        }
        
        response = self._make_request("/devices/heartbeat", data=data)
        
        if response:
            self.state = ConnectionState.CONNECTED
            self._last_heartbeat_time = time.time()
            logger.debug("Heartbeat sent successfully")
        else:
            self.state = ConnectionState.DISCONNECTED
    
    def _sync_loop(self):
        """Background loop for syncing queued detections."""
        while not self._stop_event.is_set():
            try:
                self._process_offline_queue()
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
            
            self._stop_event.wait(min(self.sync_interval, 30))
    
    def _process_offline_queue(self):
        """Process queued detections and sync to dashboard."""
        batch = []
        batch_size = 10
        
        while len(batch) < batch_size:
            try:
                payload = self._offline_queue.get_nowait()
                batch.append(payload)
            except Empty:
                break
        
        if not batch:
            return
        
        data = {
            "device_id": self.device_id,
            "detections": [p.to_dict() for p in batch]
        }
        
        response = self._make_request("/devices/detections/batch", data=data)
        
        if response:
            self._sync_success_count += len(batch)
            self._last_sync_time = time.time()
            logger.info(f"Synced {len(batch)} detections to dashboard")
        else:
            for payload in batch:
                try:
                    self._offline_queue.put_nowait(payload)
                except:
                    pass
            self._sync_failure_count += len(batch)
    
    def register_device(self, device_info: Dict[str, Any]) -> Optional[Dict]:
        """Register device with dashboard."""
        data = {
            "device_id": self.device_id,
            "info": device_info
        }
        
        response = self._make_request("/devices/register", data=data)
        
        if response:
            logger.info("Device registered with dashboard")
        
        return response
    
    def get_device_config(self) -> Optional[Dict]:
        """Fetch remote configuration from dashboard."""
        response = self._make_request(
            f"/devices/{self.device_id}/config",
            method="GET"
        )
        return response
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "state": self.state.value,
            "api_url": self.api_url,
            "device_id": self.device_id,
            "queue_size": self._offline_queue.qsize(),
            "last_sync_time": self._last_sync_time,
            "last_heartbeat_time": self._last_heartbeat_time,
            "sync_success_count": self._sync_success_count,
            "sync_failure_count": self._sync_failure_count
        }
