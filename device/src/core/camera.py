"""
Camera management for Raspberry Pi.
Supports Pi Camera Module and USB camera fallback.
"""

import logging
import time
import threading
from typing import Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class CameraType(Enum):
    PI_CAMERA = "pi_camera"
    USB_CAMERA = "usb_camera"
    SIMULATED = "simulated"


@dataclass
class CameraFrame:
    """Represents a captured frame."""
    data: np.ndarray
    timestamp: float
    width: int
    height: int
    camera_type: CameraType


class CameraManager:
    """
    Manages camera capture with automatic fallback.
    Optimized for continuous operation on Raspberry Pi.
    """
    
    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fps: int = 10,
        format: str = "RGB888",
        rotation: int = 0,
        fallback_usb: bool = True,
        usb_device_id: int = 0
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.format = format
        self.rotation = rotation
        self.fallback_usb = fallback_usb
        self.usb_device_id = usb_device_id
        
        self._camera = None
        self._camera_type: Optional[CameraType] = None
        self._is_running = False
        self._lock = threading.Lock()
        self._last_frame: Optional[CameraFrame] = None
        self._frame_count = 0
        self._error_count = 0
        self._max_consecutive_errors = 10
    
    def initialize(self) -> bool:
        """Initialize camera with automatic type detection."""
        if self._try_pi_camera():
            return True
        
        if self.fallback_usb and self._try_usb_camera():
            return True
        
        logger.warning("No camera available, using simulated mode")
        self._camera_type = CameraType.SIMULATED
        self._is_running = True
        return True
    
    def _try_pi_camera(self) -> bool:
        """Try to initialize Pi Camera."""
        try:
            from picamera2 import Picamera2
            
            self._camera = Picamera2()
            
            config = self._camera.create_preview_configuration(
                main={"size": (self.width, self.height), "format": self.format}
            )
            self._camera.configure(config)
            self._camera.start()
            
            time.sleep(0.5)
            
            self._camera_type = CameraType.PI_CAMERA
            self._is_running = True
            logger.info(f"Pi Camera initialized: {self.width}x{self.height} @ {self.fps}fps")
            return True
            
        except ImportError:
            logger.debug("picamera2 not available")
            return False
        except Exception as e:
            logger.warning(f"Pi Camera initialization failed: {e}")
            if self._camera:
                try:
                    self._camera.close()
                except:
                    pass
                self._camera = None
            return False
    
    def _try_usb_camera(self) -> bool:
        """Try to initialize USB camera via OpenCV."""
        try:
            import cv2
            
            self._camera = cv2.VideoCapture(self.usb_device_id)
            
            if not self._camera.isOpened():
                logger.debug(f"USB camera {self.usb_device_id} not available")
                return False
            
            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self._camera.set(cv2.CAP_PROP_FPS, self.fps)
            self._camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            ret, _ = self._camera.read()
            if not ret:
                self._camera.release()
                self._camera = None
                return False
            
            self._camera_type = CameraType.USB_CAMERA
            self._is_running = True
            logger.info(f"USB Camera initialized: {self.width}x{self.height}")
            return True
            
        except Exception as e:
            logger.warning(f"USB Camera initialization failed: {e}")
            if self._camera:
                try:
                    self._camera.release()
                except:
                    pass
                self._camera = None
            return False
    
    def capture(self) -> Optional[CameraFrame]:
        """Capture a single frame."""
        if not self._is_running:
            return None
        
        try:
            with self._lock:
                frame_data = self._capture_frame()
            
            if frame_data is None:
                self._handle_capture_error()
                return None
            
            self._error_count = 0
            self._frame_count += 1
            
            frame = CameraFrame(
                data=frame_data,
                timestamp=time.time(),
                width=frame_data.shape[1],
                height=frame_data.shape[0],
                camera_type=self._camera_type
            )
            self._last_frame = frame
            return frame
            
        except Exception as e:
            logger.error(f"Capture error: {e}")
            self._handle_capture_error()
            return None
    
    def _capture_frame(self) -> Optional[np.ndarray]:
        """Internal frame capture based on camera type."""
        if self._camera_type == CameraType.PI_CAMERA:
            return self._camera.capture_array()
        
        elif self._camera_type == CameraType.USB_CAMERA:
            import cv2
            ret, frame = self._camera.read()
            if ret:
                return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return None
        
        elif self._camera_type == CameraType.SIMULATED:
            return self._generate_simulated_frame()
        
        return None
    
    def _generate_simulated_frame(self) -> np.ndarray:
        """Generate a simulated frame for testing."""
        frame = np.random.randint(0, 50, (self.height, self.width, 3), dtype=np.uint8)
        frame[:, :, 1] = np.random.randint(20, 80, (self.height, self.width), dtype=np.uint8)
        return frame
    
    def _handle_capture_error(self):
        """Handle capture errors with recovery logic."""
        self._error_count += 1
        
        if self._error_count >= self._max_consecutive_errors:
            logger.error(f"Too many consecutive capture errors ({self._error_count}), attempting recovery")
            self._attempt_recovery()
    
    def _attempt_recovery(self):
        """Attempt to recover from camera errors."""
        logger.info("Attempting camera recovery...")
        
        self.stop()
        time.sleep(1)
        
        if self.initialize():
            logger.info("Camera recovery successful")
            self._error_count = 0
        else:
            logger.error("Camera recovery failed")
    
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
    
    def get_stats(self) -> dict:
        """Get camera statistics."""
        return {
            "camera_type": self._camera_type.value if self._camera_type else None,
            "is_running": self._is_running,
            "resolution": f"{self.width}x{self.height}",
            "fps": self.fps,
            "frame_count": self._frame_count,
            "error_count": self._error_count
        }
    
    @property
    def is_running(self) -> bool:
        return self._is_running
    
    @property
    def camera_type(self) -> Optional[CameraType]:
        return self._camera_type
