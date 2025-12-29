"""
API client for communicating with the Vercel dashboard.
Handles authentication, sync, and offline queue management.
Includes robust connection handling for dev/prod environments.
"""

import logging
import time
import json
import threading
import hashlib
import hmac
import ssl
import os
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from queue import Queue, Empty
from enum import Enum
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    OFFLINE = "offline"


class ConnectionError(Exception):
    """Base exception for connection errors."""
    def __init__(self, message: str, error_code: str = "CONNECTION_ERROR", recoverable: bool = True):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.recoverable = recoverable
        self.timestamp = time.time()


class AuthenticationError(ConnectionError):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_FAILED", recoverable=False)


class NetworkError(ConnectionError):
    """Raised when network is unavailable."""
    def __init__(self, message: str = "Network unavailable"):
        super().__init__(message, "NETWORK_ERROR", recoverable=True)


class ServerError(ConnectionError):
    """Raised when server returns an error."""
    def __init__(self, message: str = "Server error", status_code: int = 500):
        super().__init__(message, f"SERVER_ERROR_{status_code}", recoverable=True)
        self.status_code = status_code


@dataclass
class ConnectionConfig:
    """Configuration for connection behavior."""
    connect_timeout: int = 10
    read_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    max_retry_delay: float = 60.0
    health_check_interval: float = 30.0
    reconnect_interval: float = 5.0
    ssl_verify: bool = True
    
    @classmethod
    def for_development(cls) -> "ConnectionConfig":
        """Configuration optimized for development."""
        return cls(
            connect_timeout=5,
            read_timeout=15,
            max_retries=2,
            retry_delay=0.5,
            health_check_interval=10.0,
            reconnect_interval=2.0,
            ssl_verify=False  # Allow self-signed certs in dev
        )
    
    @classmethod
    def for_production(cls) -> "ConnectionConfig":
        """Configuration optimized for production."""
        return cls(
            connect_timeout=10,
            read_timeout=30,
            max_retries=5,
            retry_delay=1.0,
            retry_backoff=2.0,
            max_retry_delay=120.0,
            health_check_interval=60.0,
            reconnect_interval=10.0,
            ssl_verify=True
        )


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
    - Extended telemetry for comprehensive device monitoring
    - Environment-aware connection handling (dev/prod)
    - Robust error handling and recovery
    """
    
    def __init__(
        self,
        api_url: str,
        api_key: str,
        device_id: str,
        device_secret: str = "",
        sync_interval: int = 300,
        heartbeat_interval: int = 60,
        offline_queue_max_size: int = 1000,
        environment: str = "production",
        connection_config: Optional[ConnectionConfig] = None
    ):
        self.api_url = api_url.rstrip('/') if api_url else ""
        self.api_key = api_key
        self.device_id = device_id
        self.device_secret = device_secret
        self.sync_interval = sync_interval
        self.heartbeat_interval = heartbeat_interval
        self.environment = environment
        
        # Set connection config based on environment
        if connection_config:
            self.connection_config = connection_config
        elif environment == "development":
            self.connection_config = ConnectionConfig.for_development()
        else:
            self.connection_config = ConnectionConfig.for_production()
        
        self.state = ConnectionState.DISCONNECTED
        self._offline_queue: Queue = Queue(maxsize=offline_queue_max_size)
        self._stop_event = threading.Event()
        self._sync_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._health_check_thread: Optional[threading.Thread] = None
        
        self._last_sync_time: float = 0
        self._last_heartbeat_time: float = 0
        self._last_health_check_time: float = 0
        self._sync_success_count = 0
        self._sync_failure_count = 0
        self._detection_count = 0
        self._consecutive_failures = 0
        self._last_error: Optional[ConnectionError] = None
        
        self._http_client = None
        self._ssl_context = None
        self._system_monitor = None
        self._device_info: Dict[str, Any] = {}
        self._cameras: List[Dict[str, Any]] = []
        self._power_info: Dict[str, Any] = {
            "consumption_watts": None,
            "source": "unknown",
            "battery_percent": None
        }
        
        # Callbacks for connection events
        self._on_connected_callbacks: List[Callable[[], None]] = []
        self._on_disconnected_callbacks: List[Callable[[Optional[ConnectionError]], None]] = []
        self._on_error_callbacks: List[Callable[[ConnectionError], None]] = []
        
        # Initialize SSL context
        self._init_ssl_context()
        
        logger.info(f"DashboardClient initialized for {environment} environment, API URL: {self.api_url}")
    
    def _init_ssl_context(self):
        """Initialize SSL context based on environment."""
        self._ssl_context = ssl.create_default_context()
        if not self.connection_config.ssl_verify:
            # Development mode - allow self-signed certificates
            self._ssl_context.check_hostname = False
            self._ssl_context.verify_mode = ssl.CERT_NONE
            logger.debug("SSL verification disabled for development")
    
    def add_connected_callback(self, callback: Callable[[], None]):
        """Add callback for successful connection."""
        self._on_connected_callbacks.append(callback)
    
    def add_disconnected_callback(self, callback: Callable[[Optional[ConnectionError]], None]):
        """Add callback for disconnection."""
        self._on_disconnected_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[ConnectionError], None]):
        """Add callback for connection errors."""
        self._on_error_callbacks.append(callback)
    
    def _notify_connected(self):
        """Notify connected callbacks."""
        for callback in self._on_connected_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Connected callback error: {e}")
    
    def _notify_disconnected(self, error: Optional[ConnectionError] = None):
        """Notify disconnected callbacks."""
        for callback in self._on_disconnected_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Disconnected callback error: {e}")
    
    def _notify_error(self, error: ConnectionError):
        """Notify error callbacks."""
        self._last_error = error
        for callback in self._on_error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error callback error: {e}")
    
    def set_system_monitor(self, monitor) -> None:
        """Set reference to system monitor for telemetry."""
        self._system_monitor = monitor
    
    def set_device_info(self, info: Dict[str, Any]) -> None:
        """Set device information for heartbeat."""
        self._device_info = info
    
    def set_cameras(self, cameras: List[Dict[str, Any]]) -> None:
        """Set camera information for heartbeat."""
        self._cameras = cameras
    
    def set_power_info(self, power_info: Dict[str, Any]) -> None:
        """Set power information for heartbeat."""
        self._power_info = power_info
    
    def increment_detection_count(self) -> None:
        """Increment detection count."""
        self._detection_count += 1
    
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
        timeout: Optional[int] = None,
        retry: bool = True
    ) -> Optional[Dict]:
        """
        Make an HTTP request to the dashboard API with retry logic.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            data: Request payload
            timeout: Request timeout (uses config default if None)
            retry: Whether to retry on failure
            
        Returns:
            Response data dict or None on failure
        """
        http = self._get_http_client()
        if not http:
            return None
        
        if not self.api_url:
            logger.debug("No API URL configured")
            return None
        
        url = f"{self.api_url}{endpoint}"
        timeout = timeout or self.connection_config.read_timeout
        max_retries = self.connection_config.max_retries if retry else 1
        
        for attempt in range(max_retries):
            try:
                timestamp = int(time.time())
                payload = json.dumps(data) if data else ""
                signature = self._generate_signature(payload, timestamp)
                
                headers = {
                    "Content-Type": "application/json",
                    "X-API-Key": self.api_key,
                    "X-Device-ID": self.device_id,
                    "X-Timestamp": str(timestamp),
                    "X-Signature": signature,
                    "X-Environment": self.environment
                }
                
                import urllib.request
                import urllib.error
                
                req = urllib.request.Request(
                    url,
                    data=payload.encode() if payload else None,
                    headers=headers,
                    method=method
                )
                
                # Use SSL context for HTTPS
                context = self._ssl_context if url.startswith("https") else None
                
                with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
                    response_data = response.read().decode()
                    result = json.loads(response_data) if response_data else {}
                    
                    # Reset failure counter on success
                    self._consecutive_failures = 0
                    if self.state != ConnectionState.CONNECTED:
                        self.state = ConnectionState.CONNECTED
                        self._notify_connected()
                    
                    return result
                    
            except urllib.error.HTTPError as e:
                self._consecutive_failures += 1
                
                if e.code == 401:
                    error = AuthenticationError(f"Authentication failed: {e.reason}")
                    self._notify_error(error)
                    logger.error(f"Authentication error: {e.reason}")
                    return None  # Don't retry auth errors
                elif e.code >= 500:
                    error = ServerError(f"Server error: {e.reason}", e.code)
                    self._notify_error(error)
                    logger.warning(f"Server error {e.code}: {e.reason} (attempt {attempt + 1}/{max_retries})")
                else:
                    logger.error(f"HTTP error {e.code}: {e.reason}")
                    return None  # Don't retry client errors
                    
            except urllib.error.URLError as e:
                self._consecutive_failures += 1
                error = NetworkError(f"Network error: {e.reason}")
                self._notify_error(error)
                
                if self.state == ConnectionState.CONNECTED:
                    self.state = ConnectionState.DISCONNECTED
                    self._notify_disconnected(error)
                
                logger.debug(f"Network error: {e.reason} (attempt {attempt + 1}/{max_retries})")
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {e}")
                return None
                
            except Exception as e:
                self._consecutive_failures += 1
                logger.error(f"Request error: {e} (attempt {attempt + 1}/{max_retries})")
            
            # Exponential backoff before retry
            if attempt < max_retries - 1:
                delay = min(
                    self.connection_config.retry_delay * (self.connection_config.retry_backoff ** attempt),
                    self.connection_config.max_retry_delay
                )
                time.sleep(delay)
        
        # All retries failed
        if self.state != ConnectionState.ERROR:
            self.state = ConnectionState.ERROR
        return None
    
    def start(self):
        """Start background sync, heartbeat, and health check threads."""
        if not self.api_url or not self.api_key:
            logger.warning("Dashboard API not configured, running in offline mode")
            self.state = ConnectionState.OFFLINE
            return
        
        self._stop_event.clear()
        self.state = ConnectionState.CONNECTING
        
        # Initial connection test
        if self._test_connection():
            self.state = ConnectionState.CONNECTED
            logger.info(f"Connected to dashboard at {self.api_url}")
        else:
            self.state = ConnectionState.DISCONNECTED
            logger.warning(f"Initial connection to {self.api_url} failed, will retry")
        
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
        
        # Start health check thread
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            name="DashboardHealthCheck",
            daemon=True
        )
        self._health_check_thread.start()
        
        logger.info(f"Dashboard client started for {self.environment} environment")
    
    def stop(self):
        """Stop background threads."""
        self._stop_event.set()
        
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5)
        
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5)
        
        if self._health_check_thread and self._health_check_thread.is_alive():
            self._health_check_thread.join(timeout=5)
        
        self.state = ConnectionState.DISCONNECTED
        self._notify_disconnected()
        logger.info("Dashboard client stopped")
    
    def _test_connection(self) -> bool:
        """Test connection to the dashboard."""
        try:
            response = self._make_request("/health", method="GET", retry=False)
            return response is not None
        except Exception as e:
            logger.debug(f"Connection test failed: {e}")
            return False
    
    def _health_check_loop(self):
        """Background loop for connection health checks."""
        while not self._stop_event.is_set():
            try:
                self._perform_health_check()
            except Exception as e:
                logger.error(f"Health check error: {e}")
            
            self._stop_event.wait(self.connection_config.health_check_interval)
    
    def _perform_health_check(self):
        """Perform a health check and attempt reconnection if needed."""
        if self.state == ConnectionState.OFFLINE:
            return
        
        was_connected = self.state == ConnectionState.CONNECTED
        
        if self._test_connection():
            self._last_health_check_time = time.time()
            self._consecutive_failures = 0
            
            if not was_connected:
                self.state = ConnectionState.CONNECTED
                self._notify_connected()
                logger.info("Connection restored to dashboard")
        else:
            if was_connected:
                self.state = ConnectionState.DISCONNECTED
                error = NetworkError("Health check failed - connection lost")
                self._notify_disconnected(error)
                logger.warning("Lost connection to dashboard")
            
            # Attempt reconnection
            if self._consecutive_failures < self.connection_config.max_retries:
                self.state = ConnectionState.RECONNECTING
                logger.debug(f"Attempting reconnection (failure count: {self._consecutive_failures})")
    
    def check_connection(self) -> bool:
        """Check if currently connected to the dashboard."""
        return self.state == ConnectionState.CONNECTED
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get detailed connection status."""
        return {
            "state": self.state.value,
            "api_url": self.api_url,
            "environment": self.environment,
            "consecutive_failures": self._consecutive_failures,
            "last_heartbeat_time": self._last_heartbeat_time,
            "last_health_check_time": self._last_health_check_time,
            "last_error": {
                "message": self._last_error.message,
                "code": self._last_error.error_code,
                "timestamp": self._last_error.timestamp
            } if self._last_error else None,
            "config": {
                "connect_timeout": self.connection_config.connect_timeout,
                "read_timeout": self.connection_config.read_timeout,
                "max_retries": self.connection_config.max_retries,
                "ssl_verify": self.connection_config.ssl_verify
            }
        }
    
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
        """Send device heartbeat to dashboard with extended telemetry."""
        system_stats = {}
        uptime_seconds = 0
        
        if self._system_monitor:
            try:
                stats = self._system_monitor.get_stats_dict()
                system_stats = {
                    "cpu_percent": stats.get("cpu_percent", 0),
                    "memory_percent": stats.get("memory_percent", 0),
                    "memory_used_mb": stats.get("memory_used_mb", 0),
                    "memory_total_mb": stats.get("memory_available_mb", 0) + stats.get("memory_used_mb", 0),
                    "temperature_celsius": stats.get("temperature_celsius"),
                    "disk_percent": stats.get("disk_percent", 0),
                    "disk_used_gb": stats.get("disk_used_gb", 0),
                    "disk_total_gb": stats.get("disk_used_gb", 0) + stats.get("disk_free_gb", 0)
                }
                uptime_seconds = stats.get("uptime_seconds", 0)
            except Exception as e:
                logger.warning(f"Failed to get system stats: {e}")
        
        data = {
            "device_id": self.device_id,
            "timestamp": time.time(),
            "status": "online",
            "info": self._device_info,
            "stats": {
                "uptime_seconds": uptime_seconds,
                "detection_count": self._detection_count,
                "system": system_stats,
                "power": self._power_info,
                "cameras": self._cameras,
                "network": {
                    "latency_ms": self._calculate_latency()
                }
            }
        }
        
        response = self._make_request("/devices/heartbeat", data=data)
        
        if response:
            self.state = ConnectionState.CONNECTED
            self._last_heartbeat_time = time.time()
            logger.debug("Heartbeat sent successfully")
        else:
            self.state = ConnectionState.DISCONNECTED
    
    def _calculate_latency(self) -> Optional[int]:
        """Calculate network latency to dashboard."""
        if not self._last_heartbeat_time:
            return None
        try:
            start = time.time()
            response = self._make_request("/api/health", method="GET", timeout=5)
            if response:
                return int((time.time() - start) * 1000)
        except Exception:
            pass
        return None
    
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
