"""
Camera management for Raspberry Pi.
Supports Pi Camera Module and USB camera fallback.
Includes robust error handling, detection, and recovery mechanisms.
"""

import logging
import time
import threading
import platform
import os
from typing import Optional, Tuple, Callable, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class CameraType(Enum):
    PI_CAMERA = "pi_camera"
    USB_CAMERA = "usb_camera"
    SIMULATED = "simulated"
    NONE = "none"


class CameraStatus(Enum):
    """Camera operational status."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    ERROR = "error"
    RECOVERING = "recovering"
    DISCONNECTED = "disconnected"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"


class CameraError(Exception):
    """Base exception for camera errors."""
    def __init__(self, message: str, error_code: str = "CAMERA_ERROR", recoverable: bool = True):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.recoverable = recoverable
        self.timestamp = time.time()


class CameraNotFoundError(CameraError):
    """Raised when no camera is detected."""
    def __init__(self, message: str = "No camera device found"):
        super().__init__(message, "CAMERA_NOT_FOUND", recoverable=True)


class CameraPermissionError(CameraError):
    """Raised when camera access is denied."""
    def __init__(self, message: str = "Camera access denied - check permissions"):
        super().__init__(message, "CAMERA_PERMISSION_DENIED", recoverable=False)


class CameraInitializationError(CameraError):
    """Raised when camera fails to initialize."""
    def __init__(self, message: str = "Failed to initialize camera"):
        super().__init__(message, "CAMERA_INIT_FAILED", recoverable=True)


class CameraCaptureError(CameraError):
    """Raised when frame capture fails."""
    def __init__(self, message: str = "Failed to capture frame"):
        super().__init__(message, "CAMERA_CAPTURE_FAILED", recoverable=True)


@dataclass
class CameraFrame:
    """Represents a captured frame."""
    data: np.ndarray
    timestamp: float
    width: int
    height: int
    camera_type: CameraType
    frame_id: int = 0


@dataclass
class CameraDetectionResult:
    """Result of camera detection/enumeration."""
    available: bool
    camera_type: CameraType
    device_path: Optional[str] = None
    device_name: Optional[str] = None
    capabilities: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class CameraDetector:
    """
    Detects and enumerates available cameras on the system.
    Supports Pi Camera, USB cameras, and various platforms.
    """
    
    @staticmethod
    def detect_all() -> List[CameraDetectionResult]:
        """Detect all available cameras on the system."""
        results = []
        
        # Try Pi Camera first (Raspberry Pi specific)
        pi_result = CameraDetector._detect_pi_camera()
        if pi_result.available:
            results.append(pi_result)
        
        # Try USB cameras
        usb_results = CameraDetector._detect_usb_cameras()
        results.extend(usb_results)
        
        return results
    
    @staticmethod
    def _detect_pi_camera() -> CameraDetectionResult:
        """Detect Raspberry Pi camera module."""
        try:
            # Check if we're on a Raspberry Pi
            if not CameraDetector._is_raspberry_pi():
                return CameraDetectionResult(
                    available=False,
                    camera_type=CameraType.PI_CAMERA,
                    error="Not running on Raspberry Pi"
                )
            
            # Try to import picamera2
            try:
                from picamera2 import Picamera2
                
                # Check if camera is available
                cam = Picamera2()
                camera_info = cam.camera_properties
                cam.close()
                
                return CameraDetectionResult(
                    available=True,
                    camera_type=CameraType.PI_CAMERA,
                    device_path="/dev/video0",
                    device_name="Pi Camera Module",
                    capabilities={
                        "model": camera_info.get("Model", "Unknown"),
                        "max_resolution": camera_info.get("PixelArraySize", [0, 0])
                    }
                )
            except ImportError:
                return CameraDetectionResult(
                    available=False,
                    camera_type=CameraType.PI_CAMERA,
                    error="picamera2 library not installed"
                )
            except Exception as e:
                error_msg = str(e).lower()
                if "permission" in error_msg or "access" in error_msg:
                    return CameraDetectionResult(
                        available=False,
                        camera_type=CameraType.PI_CAMERA,
                        error=f"Permission denied: {e}"
                    )
                return CameraDetectionResult(
                    available=False,
                    camera_type=CameraType.PI_CAMERA,
                    error=f"Pi Camera not available: {e}"
                )
        except Exception as e:
            return CameraDetectionResult(
                available=False,
                camera_type=CameraType.PI_CAMERA,
                error=str(e)
            )
    
    @staticmethod
    def _detect_usb_cameras() -> List[CameraDetectionResult]:
        """Detect USB cameras via OpenCV."""
        results = []
        
        try:
            import cv2
        except ImportError:
            return [CameraDetectionResult(
                available=False,
                camera_type=CameraType.USB_CAMERA,
                error="OpenCV not installed"
            )]
        
        # Determine appropriate backends for the platform
        backends_to_try = [cv2.CAP_ANY]
        if platform.system() == "Darwin":  # macOS
            backends_to_try = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
        elif platform.system() == "Linux":
            backends_to_try = [cv2.CAP_V4L2, cv2.CAP_ANY]
        elif platform.system() == "Windows":
            backends_to_try = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        
        # Try multiple device indices with appropriate backends
        for device_id in range(10):  # Increased range for macOS
            for backend in backends_to_try:
                try:
                    cap = cv2.VideoCapture(device_id, backend)
                    if cap.isOpened():
                        # Get camera properties
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        
                        # Try to read a frame to verify camera works
                        ret, frame = cap.read()
                        cap.release()
                        
                        if ret and frame is not None:
                            # Get platform-specific device path
                            if platform.system() == "Linux":
                                device_path = f"/dev/video{device_id}"
                            elif platform.system() == "Darwin":
                                device_path = f"AVFoundation:{device_id}"
                            else:
                                device_path = f"device:{device_id}"
                            
                            results.append(CameraDetectionResult(
                                available=True,
                                camera_type=CameraType.USB_CAMERA,
                                device_path=device_path,
                                device_name=f"Camera {device_id}",
                                capabilities={
                                    "device_id": device_id,
                                    "width": width,
                                    "height": height,
                                    "fps": fps,
                                    "backend": CameraDetector._get_backend_name(backend)
                                }
                            ))
                            break  # Found working camera, move to next device_id
                    else:
                        cap.release()
                except Exception as e:
                    error_msg = str(e).lower()
                    if "permission" in error_msg:
                        results.append(CameraDetectionResult(
                            available=False,
                            camera_type=CameraType.USB_CAMERA,
                            device_path=f"device:{device_id}",
                            error=f"Permission denied for device {device_id}"
                        ))
                        break
        
        if not results:
            results.append(CameraDetectionResult(
                available=False,
                camera_type=CameraType.USB_CAMERA,
                error="No USB cameras detected"
            ))
        
        return results
    
    @staticmethod
    def _is_raspberry_pi() -> bool:
        """Check if running on Raspberry Pi."""
        try:
            # Check /proc/cpuinfo for Raspberry Pi
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r") as f:
                    cpuinfo = f.read().lower()
                    if "raspberry" in cpuinfo or "bcm" in cpuinfo:
                        return True
            
            # Check /proc/device-tree/model
            if os.path.exists("/proc/device-tree/model"):
                with open("/proc/device-tree/model", "r") as f:
                    model = f.read().lower()
                    if "raspberry" in model:
                        return True
            
            return False
        except Exception:
            return False
    
    @staticmethod
    def get_best_camera() -> Optional[CameraDetectionResult]:
        """Get the best available camera (Pi Camera preferred)."""
        cameras = CameraDetector.detect_all()
        available = [c for c in cameras if c.available]
        
        if not available:
            return None
        
        # Prefer Pi Camera
        for cam in available:
            if cam.camera_type == CameraType.PI_CAMERA:
                return cam
        
        # Fall back to first USB camera
        return available[0]
    
    @staticmethod
    def _get_backend_name(backend) -> str:
        """Get human-readable backend name."""
        try:
            import cv2
            backend_names = {
                cv2.CAP_ANY: "Any",
                cv2.CAP_V4L2: "V4L2",
                cv2.CAP_AVFOUNDATION: "AVFoundation",
                cv2.CAP_DSHOW: "DirectShow",
                cv2.CAP_MSMF: "Media Foundation"
            }
            return backend_names.get(backend, "Unknown")
        except Exception:
            return "Unknown"


class CameraManager:
    """
    Manages camera capture with automatic fallback.
    Optimized for continuous operation on Raspberry Pi.
    Includes robust error handling and recovery mechanisms.
    """
    
    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fps: int = 10,
        format: str = "RGB888",
        rotation: int = 0,
        fallback_usb: bool = True,
        usb_device_id: int = 0,
        auto_recovery: bool = True,
        max_recovery_attempts: int = 3,
        recovery_delay: float = 2.0
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.format = format
        self.rotation = rotation
        self.fallback_usb = fallback_usb
        self.usb_device_id = usb_device_id
        self.auto_recovery = auto_recovery
        self.max_recovery_attempts = max_recovery_attempts
        self.recovery_delay = recovery_delay
        
        self._camera = None
        self._camera_type: CameraType = CameraType.NONE
        self._status: CameraStatus = CameraStatus.UNINITIALIZED
        self._is_running = False
        self._lock = threading.Lock()
        self._last_frame: Optional[CameraFrame] = None
        self._frame_count = 0
        self._error_count = 0
        self._total_error_count = 0
        self._max_consecutive_errors = 10
        self._recovery_attempts = 0
        self._last_error: Optional[CameraError] = None
        self._last_successful_capture: Optional[float] = None
        self._initialization_time: Optional[float] = None
        self._error_callbacks: List[Callable[[CameraError], None]] = []
        self._status_callbacks: List[Callable[[CameraStatus], None]] = []
        self._camera_info: Dict[str, Any] = {}
    
    def add_error_callback(self, callback: Callable[[CameraError], None]):
        """Add callback for camera errors."""
        self._error_callbacks.append(callback)
    
    def add_status_callback(self, callback: Callable[[CameraStatus], None]):
        """Add callback for status changes."""
        self._status_callbacks.append(callback)
    
    def _set_status(self, status: CameraStatus):
        """Update camera status and notify callbacks."""
        if self._status != status:
            old_status = self._status
            self._status = status
            logger.debug(f"Camera status changed: {old_status.value} -> {status.value}")
            for callback in self._status_callbacks:
                try:
                    callback(status)
                except Exception as e:
                    logger.error(f"Status callback error: {e}")
    
    def _notify_error(self, error: CameraError):
        """Notify error callbacks."""
        self._last_error = error
        for callback in self._error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error callback error: {e}")
    
    def initialize(self) -> bool:
        """
        Initialize camera with automatic type detection.
        
        Returns:
            True if camera initialized successfully (including simulated mode)
        """
        self._set_status(CameraStatus.INITIALIZING)
        self._initialization_time = time.time()
        
        # First, detect available cameras
        detection_results = CameraDetector.detect_all()
        available_cameras = [r for r in detection_results if r.available]
        
        if not available_cameras:
            # Check for permission errors
            permission_errors = [r for r in detection_results if r.error and "permission" in r.error.lower()]
            if permission_errors:
                error = CameraPermissionError(permission_errors[0].error)
                self._notify_error(error)
                self._set_status(CameraStatus.PERMISSION_DENIED)
                logger.error(f"Camera permission denied: {permission_errors[0].error}")
            else:
                logger.warning("No cameras detected on system")
                self._set_status(CameraStatus.NOT_FOUND)
        
        # Try Pi Camera first
        if self._try_pi_camera():
            self._set_status(CameraStatus.READY)
            return True
        
        # Try USB camera fallback
        if self.fallback_usb and self._try_usb_camera():
            self._set_status(CameraStatus.READY)
            return True
        
        # Fall back to simulated mode
        logger.warning("No physical camera available, using simulated mode")
        self._camera_type = CameraType.SIMULATED
        self._is_running = True
        
        # Store simulated camera info
        self._camera_info = {
            "type": "simulated",
            "name": "Simulated Camera",
            "model": "Virtual",
            "device_path": "virtual",
            "resolution": f"{self.width}x{self.height}",
            "fps": self.fps
        }
        
        self._set_status(CameraStatus.READY)
        return True
    
    def _try_pi_camera(self) -> bool:
        """Try to initialize Pi Camera with detailed error handling."""
        try:
            from picamera2 import Picamera2
            
            logger.debug("Attempting Pi Camera initialization...")
            self._camera = Picamera2()
            
            config = self._camera.create_preview_configuration(
                main={"size": (self.width, self.height), "format": self.format}
            )
            self._camera.configure(config)
            self._camera.start()
            
            # Wait for camera to stabilize and verify it's working
            time.sleep(0.5)
            
            # Verify we can capture a frame
            test_frame = self._camera.capture_array()
            if test_frame is None or test_frame.size == 0:
                raise CameraInitializationError("Pi Camera started but cannot capture frames")
            
            self._camera_type = CameraType.PI_CAMERA
            self._is_running = True
            self._recovery_attempts = 0
            
            # Store camera info
            camera_props = self._camera.camera_properties
            self._camera_info = {
                "type": "pi_camera",
                "name": "Raspberry Pi Camera",
                "model": camera_props.get("Model", "Unknown"),
                "device_path": "/dev/video0",
                "resolution": f"{self.width}x{self.height}",
                "fps": self.fps
            }
            
            logger.info(f"Pi Camera initialized: {self.width}x{self.height} @ {self.fps}fps")
            return True
            
        except ImportError:
            logger.debug("picamera2 not available - not on Raspberry Pi or library not installed")
            return False
        except PermissionError as e:
            error = CameraPermissionError(f"Pi Camera permission denied: {e}")
            self._notify_error(error)
            logger.error(str(error))
            self._cleanup_pi_camera()
            return False
        except Exception as e:
            error_msg = str(e).lower()
            if "permission" in error_msg or "access denied" in error_msg:
                error = CameraPermissionError(f"Pi Camera access denied: {e}")
                self._notify_error(error)
                logger.error(str(error))
            else:
                logger.warning(f"Pi Camera initialization failed: {e}")
            self._cleanup_pi_camera()
            return False
    
    def _cleanup_pi_camera(self):
        """Safely cleanup Pi Camera resources."""
        if self._camera:
            try:
                self._camera.stop()
            except Exception:
                pass
            try:
                self._camera.close()
            except Exception:
                pass
            self._camera = None
    
    def _try_usb_camera(self) -> bool:
        """Try to initialize USB camera via OpenCV with detailed error handling."""
        try:
            import cv2
        except ImportError:
            logger.debug("OpenCV not available for USB camera")
            return False
        
        # Try the specified device ID first, then scan others
        device_ids_to_try = [self.usb_device_id]
        if self.usb_device_id != 0:
            device_ids_to_try.append(0)
        device_ids_to_try.extend([i for i in range(1, 5) if i not in device_ids_to_try])
        
        for device_id in device_ids_to_try:
            try:
                logger.debug(f"Attempting USB camera initialization on device {device_id}...")
                
                # Try different backends on different platforms
                backends = [cv2.CAP_ANY]
                if platform.system() == "Linux":
                    backends = [cv2.CAP_V4L2, cv2.CAP_ANY]
                elif platform.system() == "Darwin":  # macOS
                    backends = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
                elif platform.system() == "Windows":
                    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
                
                for backend in backends:
                    try:
                        self._camera = cv2.VideoCapture(device_id, backend)
                        
                        if not self._camera.isOpened():
                            self._camera.release()
                            continue
                        
                        # Configure camera
                        self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                        self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                        self._camera.set(cv2.CAP_PROP_FPS, self.fps)
                        self._camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        
                        # Verify camera works by reading a frame
                        ret, frame = self._camera.read()
                        if not ret or frame is None or frame.size == 0:
                            self._camera.release()
                            continue
                        
                        # Success!
                        actual_width = int(self._camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                        actual_height = int(self._camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        
                        self._camera_type = CameraType.USB_CAMERA
                        self.usb_device_id = device_id  # Update to working device
                        self._is_running = True
                        self._recovery_attempts = 0
                        
                        # Store camera info
                        device_path = f"/dev/video{device_id}" if platform.system() == "Linux" else f"device:{device_id}"
                        self._camera_info = {
                            "type": "usb_camera",
                            "name": f"USB Camera {device_id}",
                            "model": "Unknown",
                            "device_path": device_path,
                            "device_id": device_id,
                            "resolution": f"{actual_width}x{actual_height}",
                            "fps": self.fps,
                            "backend": self._get_backend_name(backend)
                        }
                        
                        logger.info(f"USB Camera initialized: device {device_id}, {actual_width}x{actual_height}")
                        return True
                        
                    except Exception as e:
                        if self._camera:
                            try:
                                self._camera.release()
                            except Exception:
                                pass
                            self._camera = None
                        continue
                        
            except PermissionError as e:
                error = CameraPermissionError(f"USB Camera {device_id} permission denied: {e}")
                self._notify_error(error)
                logger.error(str(error))
            except Exception as e:
                error_msg = str(e).lower()
                if "permission" in error_msg or "access" in error_msg:
                    error = CameraPermissionError(f"USB Camera {device_id} access denied: {e}")
                    self._notify_error(error)
                    logger.error(str(error))
                else:
                    logger.debug(f"USB Camera {device_id} initialization failed: {e}")
        
        logger.warning("No USB cameras available")
        return False
    
    def _get_backend_name(self, backend) -> str:
        """Get human-readable backend name."""
        try:
            import cv2
            backend_names = {
                cv2.CAP_ANY: "Any",
                cv2.CAP_V4L2: "V4L2",
                cv2.CAP_AVFOUNDATION: "AVFoundation",
                cv2.CAP_DSHOW: "DirectShow",
                cv2.CAP_MSMF: "Media Foundation"
            }
            return backend_names.get(backend, "Unknown")
        except Exception:
            return "Unknown"
    
    def capture(self) -> Optional[CameraFrame]:
        """
        Capture a single frame.
        
        Returns:
            CameraFrame if successful, None if capture failed
        """
        if not self._is_running:
            return None
        
        if self._status == CameraStatus.RECOVERING:
            return None
        
        try:
            with self._lock:
                frame_data = self._capture_frame()
            
            if frame_data is None:
                self._handle_capture_error(CameraCaptureError("Frame capture returned None"))
                return None
            
            # Validate frame data
            if frame_data.size == 0:
                self._handle_capture_error(CameraCaptureError("Frame capture returned empty data"))
                return None
            
            self._error_count = 0
            self._frame_count += 1
            self._last_successful_capture = time.time()
            
            if self._status != CameraStatus.RUNNING:
                self._set_status(CameraStatus.RUNNING)
            
            frame = CameraFrame(
                data=frame_data,
                timestamp=time.time(),
                width=frame_data.shape[1],
                height=frame_data.shape[0],
                camera_type=self._camera_type,
                frame_id=self._frame_count
            )
            self._last_frame = frame
            return frame
            
        except Exception as e:
            error = CameraCaptureError(f"Capture exception: {e}")
            logger.error(f"Capture error: {e}")
            self._handle_capture_error(error)
            return None
    
    def _capture_frame(self) -> Optional[np.ndarray]:
        """Internal frame capture based on camera type."""
        if self._camera_type == CameraType.PI_CAMERA:
            if self._camera is None:
                return None
            try:
                return self._camera.capture_array()
            except Exception as e:
                logger.debug(f"Pi Camera capture failed: {e}")
                return None
        
        elif self._camera_type == CameraType.USB_CAMERA:
            if self._camera is None:
                return None
            try:
                import cv2
                ret, frame = self._camera.read()
                if ret and frame is not None:
                    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return None
            except Exception as e:
                logger.debug(f"USB Camera capture failed: {e}")
                return None
        
        elif self._camera_type == CameraType.SIMULATED:
            return self._generate_simulated_frame()
        
        return None
    
    def _generate_simulated_frame(self) -> np.ndarray:
        """Generate a simulated frame for testing."""
        frame = np.random.randint(0, 50, (self.height, self.width, 3), dtype=np.uint8)
        frame[:, :, 1] = np.random.randint(20, 80, (self.height, self.width), dtype=np.uint8)
        return frame
    
    def _handle_capture_error(self, error: Optional[CameraError] = None):
        """Handle capture errors with recovery logic."""
        self._error_count += 1
        self._total_error_count += 1
        
        if error:
            self._notify_error(error)
        
        if self._error_count >= self._max_consecutive_errors:
            logger.error(f"Too many consecutive capture errors ({self._error_count}), attempting recovery")
            self._set_status(CameraStatus.ERROR)
            
            if self.auto_recovery:
                self._attempt_recovery()
            else:
                logger.warning("Auto-recovery disabled, camera in error state")
    
    def _attempt_recovery(self):
        """Attempt to recover from camera errors with exponential backoff."""
        if self._recovery_attempts >= self.max_recovery_attempts:
            logger.error(f"Max recovery attempts ({self.max_recovery_attempts}) reached, giving up")
            self._set_status(CameraStatus.ERROR)
            error = CameraInitializationError(
                f"Camera recovery failed after {self.max_recovery_attempts} attempts"
            )
            self._notify_error(error)
            return
        
        self._recovery_attempts += 1
        self._set_status(CameraStatus.RECOVERING)
        
        # Exponential backoff
        delay = self.recovery_delay * (2 ** (self._recovery_attempts - 1))
        logger.info(f"Attempting camera recovery (attempt {self._recovery_attempts}/{self.max_recovery_attempts}) after {delay:.1f}s delay...")
        
        self.stop()
        time.sleep(delay)
        
        if self.initialize():
            logger.info(f"Camera recovery successful on attempt {self._recovery_attempts}")
            self._error_count = 0
            self._set_status(CameraStatus.READY)
        else:
            logger.warning(f"Camera recovery attempt {self._recovery_attempts} failed")
            if self._recovery_attempts < self.max_recovery_attempts:
                # Schedule another recovery attempt
                self._attempt_recovery()
    
    def stop(self):
        """Stop camera capture and release resources."""
        self._is_running = False
        
        with self._lock:
            if self._camera:
                try:
                    if self._camera_type == CameraType.PI_CAMERA:
                        self._camera.stop()
                        self._camera.close()
                    elif self._camera_type == CameraType.USB_CAMERA:
                        self._camera.release()
                except Exception as e:
                    logger.warning(f"Error stopping camera: {e}")
                finally:
                    self._camera = None
        
        logger.info("Camera stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive camera statistics."""
        uptime = None
        if self._initialization_time:
            uptime = time.time() - self._initialization_time
        
        time_since_last_capture = None
        if self._last_successful_capture:
            time_since_last_capture = time.time() - self._last_successful_capture
        
        return {
            "camera_type": self._camera_type.value if self._camera_type else None,
            "status": self._status.value,
            "is_running": self._is_running,
            "resolution": f"{self.width}x{self.height}",
            "fps": self.fps,
            "frame_count": self._frame_count,
            "error_count": self._error_count,
            "total_error_count": self._total_error_count,
            "recovery_attempts": self._recovery_attempts,
            "uptime_seconds": round(uptime, 1) if uptime else None,
            "last_capture_ago_seconds": round(time_since_last_capture, 1) if time_since_last_capture else None,
            "last_error": {
                "message": self._last_error.message,
                "code": self._last_error.error_code,
                "timestamp": self._last_error.timestamp
            } if self._last_error else None
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get camera health status for monitoring."""
        healthy = (
            self._is_running and 
            self._status in [CameraStatus.READY, CameraStatus.RUNNING] and
            self._error_count < self._max_consecutive_errors // 2
        )
        
        issues = []
        if not self._is_running:
            issues.append("Camera not running")
        if self._status == CameraStatus.ERROR:
            issues.append("Camera in error state")
        if self._status == CameraStatus.PERMISSION_DENIED:
            issues.append("Camera permission denied")
        if self._status == CameraStatus.NOT_FOUND:
            issues.append("No camera found")
        if self._error_count > 0:
            issues.append(f"{self._error_count} consecutive errors")
        if self._last_successful_capture:
            time_since = time.time() - self._last_successful_capture
            if time_since > 30:
                issues.append(f"No capture for {time_since:.0f}s")
        
        return {
            "healthy": healthy,
            "status": self._status.value,
            "camera_type": self._camera_type.value if self._camera_type else None,
            "issues": issues,
            "recoverable": self._last_error.recoverable if self._last_error else True
        }
    
    @property
    def is_running(self) -> bool:
        return self._is_running
    
    @property
    def status(self) -> CameraStatus:
        return self._status
    
    @property
    def camera_type(self) -> CameraType:
        return self._camera_type
    
    @property
    def last_error(self) -> Optional[CameraError]:
        return self._last_error
    
    def get_camera_info(self) -> Dict[str, Any]:
        """Get camera information for reporting to portal."""
        if not self._camera_info:
            # Return unknown if camera not initialized
            return {
                "type": "unknown",
                "name": "Unknown Camera",
                "model": "Unknown",
                "device_path": "unknown",
                "resolution": f"{self.width}x{self.height}",
                "fps": self.fps,
                "status": self._status.value
            }
        
        # Add current status to info
        info = self._camera_info.copy()
        info["status"] = self._status.value
        info["is_running"] = self._is_running
        return info


class MultiCameraManager:
    """
    Manages multiple cameras for simultaneous detection.
    Auto-detects all available cameras (1 to N) without manual configuration.
    """
    
    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fps: int = 10,
        format: str = "RGB888",
        rotation: int = 0,
        max_cameras: int = 10,
        auto_recovery: bool = True
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.format = format
        self.rotation = rotation
        self.max_cameras = max_cameras
        self.auto_recovery = auto_recovery
        
        self._cameras: Dict[str, Dict[str, Any]] = {}  # camera_id -> {camera, info}
        self._lock = threading.Lock()
        self._is_running = False
        self._frame_counts: Dict[str, int] = {}
        self._error_callbacks: List[Callable[[str, CameraError], None]] = []
        self._status_callbacks: List[Callable[[str, CameraStatus], None]] = []
        
        logger.info(f"MultiCameraManager initialized (max cameras: {max_cameras})")
    
    def add_error_callback(self, callback: Callable[[str, CameraError], None]):
        """Add callback for camera errors. Receives (camera_id, error)."""
        self._error_callbacks.append(callback)
    
    def add_status_callback(self, callback: Callable[[str, CameraStatus], None]):
        """Add callback for status changes. Receives (camera_id, status)."""
        self._status_callbacks.append(callback)
    
    def _notify_error(self, camera_id: str, error: CameraError):
        """Notify error callbacks."""
        for callback in self._error_callbacks:
            try:
                callback(camera_id, error)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")
    
    def _notify_status(self, camera_id: str, status: CameraStatus):
        """Notify status callbacks."""
        for callback in self._status_callbacks:
            try:
                callback(camera_id, status)
            except Exception as e:
                logger.error(f"Status callback failed: {e}")
    
    def auto_detect_and_initialize(self) -> int:
        """
        Auto-detect and initialize all available cameras.
        Returns the number of cameras successfully initialized.
        """
        logger.info("Auto-detecting all available cameras...")
        
        cameras_found = 0
        
        # First try Pi Camera
        if self._try_add_pi_camera():
            cameras_found += 1
        
        # Then detect all USB cameras
        usb_cameras = self._detect_all_usb_cameras()
        for device_id in usb_cameras:
            if self._try_add_usb_camera(device_id):
                cameras_found += 1
                if cameras_found >= self.max_cameras:
                    logger.info(f"Reached max camera limit ({self.max_cameras})")
                    break
        
        if cameras_found == 0:
            # Add simulated camera as fallback
            logger.warning("No physical cameras found, adding simulated camera")
            self._add_simulated_camera()
            cameras_found = 1
        
        self._is_running = cameras_found > 0
        logger.info(f"Auto-detection complete: {cameras_found} camera(s) initialized")
        
        return cameras_found
    
    def initialize(self) -> bool:
        """Initialize cameras (alias for auto_detect_and_initialize)."""
        return self.auto_detect_and_initialize() > 0
    
    def _detect_all_usb_cameras(self) -> List[int]:
        """Detect all available USB camera device IDs."""
        available_devices = []
        
        try:
            import cv2
        except ImportError:
            logger.warning("OpenCV not available for USB camera detection")
            return []
        
        # Determine backend based on platform
        if platform.system() == "Darwin":  # macOS
            backend = cv2.CAP_AVFOUNDATION
        elif platform.system() == "Linux":
            backend = cv2.CAP_V4L2
        elif platform.system() == "Windows":
            backend = cv2.CAP_DSHOW
        else:
            backend = cv2.CAP_ANY
        
        logger.debug(f"Scanning for USB cameras (backend: {backend})...")
        
        # Scan device IDs 0 to max_cameras
        for device_id in range(self.max_cameras + 5):  # Check a few extra
            try:
                cap = cv2.VideoCapture(device_id, backend)
                if cap.isOpened():
                    # Try to read a frame to verify camera works
                    ret, frame = cap.read()
                    cap.release()
                    
                    if ret and frame is not None and frame.size > 0:
                        logger.debug(f"Found working camera at device {device_id}")
                        available_devices.append(device_id)
                else:
                    cap.release()
            except Exception as e:
                logger.debug(f"Error checking device {device_id}: {e}")
        
        logger.info(f"Detected {len(available_devices)} USB camera(s): {available_devices}")
        return available_devices
    
    def _try_add_pi_camera(self) -> bool:
        """Try to add Pi Camera."""
        try:
            from picamera2 import Picamera2
            
            if not CameraDetector._is_raspberry_pi():
                return False
            
            logger.debug("Attempting to add Pi Camera...")
            
            camera = Picamera2()
            config = camera.create_preview_configuration(
                main={"size": (self.width, self.height), "format": self.format}
            )
            camera.configure(config)
            camera.start()
            time.sleep(0.5)
            
            # Verify it works
            test_frame = camera.capture_array()
            if test_frame is None or test_frame.size == 0:
                camera.stop()
                camera.close()
                return False
            
            camera_id = "pi_camera_0"
            camera_props = camera.camera_properties
            
            self._cameras[camera_id] = {
                "camera": camera,
                "type": CameraType.PI_CAMERA,
                "info": {
                    "type": "pi_camera",
                    "name": "Raspberry Pi Camera",
                    "model": camera_props.get("Model", "Unknown"),
                    "device_path": "/dev/video0",
                    "device_id": 0,
                    "resolution": f"{self.width}x{self.height}",
                    "fps": self.fps
                },
                "status": CameraStatus.RUNNING
            }
            self._frame_counts[camera_id] = 0
            
            logger.info(f"Added Pi Camera as {camera_id}")
            self._notify_status(camera_id, CameraStatus.RUNNING)
            return True
            
        except ImportError:
            logger.debug("picamera2 not available")
            return False
        except Exception as e:
            logger.debug(f"Failed to add Pi Camera: {e}")
            return False
    
    def _try_add_usb_camera(self, device_id: int) -> bool:
        """Try to add a USB camera."""
        try:
            import cv2
        except ImportError:
            return False
        
        camera_id = f"usb_camera_{device_id}"
        
        # Skip if already added
        if camera_id in self._cameras:
            return False
        
        logger.debug(f"Attempting to add USB camera at device {device_id}...")
        
        # Determine backend
        if platform.system() == "Darwin":
            backend = cv2.CAP_AVFOUNDATION
        elif platform.system() == "Linux":
            backend = cv2.CAP_V4L2
        elif platform.system() == "Windows":
            backend = cv2.CAP_DSHOW
        else:
            backend = cv2.CAP_ANY
        
        try:
            camera = cv2.VideoCapture(device_id, backend)
            
            if not camera.isOpened():
                camera.release()
                return False
            
            # Configure camera
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            camera.set(cv2.CAP_PROP_FPS, self.fps)
            camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Verify camera works
            ret, frame = camera.read()
            if not ret or frame is None or frame.size == 0:
                camera.release()
                return False
            
            actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            device_path = f"/dev/video{device_id}" if platform.system() == "Linux" else f"device:{device_id}"
            
            self._cameras[camera_id] = {
                "camera": camera,
                "type": CameraType.USB_CAMERA,
                "info": {
                    "type": "usb_camera",
                    "name": f"USB Camera {device_id}",
                    "model": "Unknown",
                    "device_path": device_path,
                    "device_id": device_id,
                    "resolution": f"{actual_width}x{actual_height}",
                    "fps": self.fps
                },
                "status": CameraStatus.RUNNING
            }
            self._frame_counts[camera_id] = 0
            
            logger.info(f"Added USB Camera {device_id} as {camera_id} ({actual_width}x{actual_height})")
            self._notify_status(camera_id, CameraStatus.RUNNING)
            return True
            
        except Exception as e:
            logger.warning(f"Failed to add USB camera {device_id}: {e}")
            return False
    
    def _add_simulated_camera(self):
        """Add a simulated camera for testing."""
        camera_id = "simulated_0"
        
        self._cameras[camera_id] = {
            "camera": None,
            "type": CameraType.SIMULATED,
            "info": {
                "type": "simulated",
                "name": "Simulated Camera",
                "model": "Virtual",
                "device_path": "virtual",
                "device_id": 0,
                "resolution": f"{self.width}x{self.height}",
                "fps": self.fps
            },
            "status": CameraStatus.RUNNING
        }
        self._frame_counts[camera_id] = 0
        logger.info(f"Added simulated camera as {camera_id}")
    
    def capture_all(self) -> List[Tuple[str, CameraFrame]]:
        """
        Capture frames from all cameras simultaneously.
        Returns list of (camera_id, frame) tuples.
        """
        frames = []
        
        with self._lock:
            for camera_id, cam_data in list(self._cameras.items()):
                try:
                    frame = self._capture_from_camera(camera_id, cam_data)
                    if frame:
                        frames.append((camera_id, frame))
                except Exception as e:
                    logger.error(f"Error capturing from {camera_id}: {e}")
                    self._handle_camera_error(camera_id, e)
        
        return frames
    
    def capture_from(self, camera_id: str) -> Optional[CameraFrame]:
        """Capture a frame from a specific camera."""
        with self._lock:
            if camera_id not in self._cameras:
                return None
            
            cam_data = self._cameras[camera_id]
            return self._capture_from_camera(camera_id, cam_data)
    
    def _capture_from_camera(self, camera_id: str, cam_data: Dict) -> Optional[CameraFrame]:
        """Internal capture from a specific camera."""
        camera_type = cam_data["type"]
        camera = cam_data["camera"]
        
        frame_data = None
        
        if camera_type == CameraType.PI_CAMERA:
            if camera:
                try:
                    frame_data = camera.capture_array()
                except Exception as e:
                    logger.debug(f"Pi Camera capture failed: {e}")
        
        elif camera_type == CameraType.USB_CAMERA:
            if camera:
                try:
                    import cv2
                    ret, frame = camera.read()
                    if ret and frame is not None:
                        frame_data = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                except Exception as e:
                    logger.debug(f"USB Camera capture failed: {e}")
        
        elif camera_type == CameraType.SIMULATED:
            frame_data = np.random.randint(0, 50, (self.height, self.width, 3), dtype=np.uint8)
            frame_data[:, :, 1] = np.random.randint(20, 80, (self.height, self.width), dtype=np.uint8)
        
        if frame_data is not None and frame_data.size > 0:
            self._frame_counts[camera_id] = self._frame_counts.get(camera_id, 0) + 1
            
            return CameraFrame(
                data=frame_data,
                timestamp=time.time(),
                width=frame_data.shape[1],
                height=frame_data.shape[0],
                camera_type=camera_type,
                frame_id=self._frame_counts[camera_id]
            )
        
        return None
    
    def _handle_camera_error(self, camera_id: str, error: Exception):
        """Handle camera error and attempt recovery."""
        cam_data = self._cameras.get(camera_id)
        if not cam_data:
            return
        
        cam_data["status"] = CameraStatus.ERROR
        
        camera_error = CameraCaptureError(f"Camera {camera_id} error: {error}")
        self._notify_error(camera_id, camera_error)
        
        if self.auto_recovery:
            logger.info(f"Attempting to recover camera {camera_id}...")
            self._attempt_camera_recovery(camera_id)
    
    def _attempt_camera_recovery(self, camera_id: str):
        """Attempt to recover a failed camera."""
        cam_data = self._cameras.get(camera_id)
        if not cam_data:
            return
        
        # Release old camera
        camera = cam_data.get("camera")
        camera_type = cam_data["type"]
        
        if camera:
            try:
                if camera_type == CameraType.PI_CAMERA:
                    camera.stop()
                    camera.close()
                elif camera_type == CameraType.USB_CAMERA:
                    camera.release()
            except Exception:
                pass
        
        # Remove from dict temporarily
        device_id = cam_data["info"].get("device_id", 0)
        del self._cameras[camera_id]
        
        time.sleep(1)  # Brief delay before retry
        
        # Try to re-add
        if camera_type == CameraType.PI_CAMERA:
            self._try_add_pi_camera()
        elif camera_type == CameraType.USB_CAMERA:
            self._try_add_usb_camera(device_id)
    
    def get_camera_ids(self) -> List[str]:
        """Get list of active camera IDs."""
        return list(self._cameras.keys())
    
    def get_camera_count(self) -> int:
        """Get number of active cameras."""
        return len(self._cameras)
    
    def get_camera_info(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Get info for a specific camera."""
        cam_data = self._cameras.get(camera_id)
        if cam_data:
            info = cam_data["info"].copy()
            info["status"] = cam_data["status"].value
            info["frame_count"] = self._frame_counts.get(camera_id, 0)
            return info
        return None
    
    def get_all_cameras_info(self) -> List[Dict[str, Any]]:
        """Get info for all cameras."""
        cameras_info = []
        for camera_id in self._cameras:
            info = self.get_camera_info(camera_id)
            if info:
                info["camera_id"] = camera_id
                cameras_info.append(info)
        return cameras_info
    
    def stop(self):
        """Stop all cameras and release resources."""
        self._is_running = False
        
        with self._lock:
            for camera_id, cam_data in list(self._cameras.items()):
                try:
                    camera = cam_data.get("camera")
                    camera_type = cam_data["type"]
                    
                    if camera:
                        if camera_type == CameraType.PI_CAMERA:
                            camera.stop()
                            camera.close()
                        elif camera_type == CameraType.USB_CAMERA:
                            camera.release()
                    
                    logger.debug(f"Released camera {camera_id}")
                except Exception as e:
                    logger.warning(f"Error releasing camera {camera_id}: {e}")
            
            self._cameras.clear()
        
        logger.info("All cameras stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all cameras."""
        total_frames = sum(self._frame_counts.values())
        
        return {
            "camera_count": len(self._cameras),
            "total_frames": total_frames,
            "is_running": self._is_running,
            "cameras": self.get_all_cameras_info()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for all cameras."""
        healthy_count = sum(
            1 for cam_data in self._cameras.values()
            if cam_data["status"] in [CameraStatus.READY, CameraStatus.RUNNING]
        )
        
        issues = []
        if not self._cameras:
            issues.append("No cameras available")
        
        for camera_id, cam_data in self._cameras.items():
            if cam_data["status"] == CameraStatus.ERROR:
                issues.append(f"{camera_id}: in error state")
            elif cam_data["status"] == CameraStatus.PERMISSION_DENIED:
                issues.append(f"{camera_id}: permission denied")
        
        return {
            "healthy": healthy_count == len(self._cameras) and len(self._cameras) > 0,
            "total_cameras": len(self._cameras),
            "healthy_cameras": healthy_count,
            "issues": issues
        }
    
    @property
    def is_running(self) -> bool:
        return self._is_running
