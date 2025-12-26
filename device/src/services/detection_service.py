"""
Main detection service that orchestrates camera, detector, and storage.
Designed for continuous 24/7 operation with robust error handling.
"""

import logging
import time
import threading
import signal
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from queue import Queue, Empty
from enum import Enum

from ..core.config import Config
from ..core.detector import WildlifeDetector, Detection
from ..core.camera import CameraManager, CameraFrame
from ..storage.database import DetectionDatabase, DetectionRecord
from ..storage.image_store import ImageStore

logger = logging.getLogger(__name__)


class ServiceState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPING = "stopping"


@dataclass
class DetectionEvent:
    """Event containing detection results for a frame."""
    frame: CameraFrame
    detections: List[Detection]
    processing_time_ms: float
    timestamp: float


class DetectionService:
    """
    Main service orchestrating wildlife detection.
    
    Features:
    - Continuous camera capture and detection
    - Automatic error recovery
    - Detection cooldown to prevent alert spam
    - Callback system for alerts
    - Resource monitoring
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.state = ServiceState.STOPPED
        
        self.camera: Optional[CameraManager] = None
        self.detector: Optional[WildlifeDetector] = None
        self.database: Optional[DetectionDatabase] = None
        self.image_store: Optional[ImageStore] = None
        
        self._detection_callbacks: List[Callable[[DetectionEvent], None]] = []
        self._detection_queue: Queue = Queue(maxsize=100)
        
        self._main_thread: Optional[threading.Thread] = None
        self._processing_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        self._last_detection_time: Dict[str, float] = {}
        self._frame_count = 0
        self._detection_count = 0
        self._error_count = 0
        self._start_time: Optional[float] = None
        
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.stop()
        
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        except Exception:
            pass
    
    def initialize(self) -> bool:
        """Initialize all components."""
        self.state = ServiceState.STARTING
        logger.info("Initializing detection service...")
        
        try:
            base_path = self.config.get_base_path()
            
            self.database = DetectionDatabase(
                db_path=str(base_path / self.config.storage.database.path),
                max_size_mb=self.config.storage.database.max_size_mb
            )
            if not self.database.initialize():
                raise RuntimeError("Database initialization failed")
            
            self.image_store = ImageStore(
                base_path=str(base_path / self.config.storage.images.path),
                jpeg_quality=self.config.storage.images.jpeg_quality,
                max_storage_mb=self.config.storage.images.max_storage_mb,
                cleanup_days=self.config.storage.images.cleanup_days
            )
            if not self.image_store.initialize():
                raise RuntimeError("Image store initialization failed")
            
            self.detector = WildlifeDetector(
                model_path=str(base_path / self.config.detection.model.path),
                fallback_path=str(base_path / self.config.detection.model.fallback_path),
                confidence_threshold=self.config.detection.model.confidence_threshold,
                iou_threshold=self.config.detection.model.iou_threshold,
                target_classes=self.config.detection.target_classes,
                use_ncnn=self.config.detection.use_ncnn,
                num_threads=self.config.detection.num_threads
            )
            if not self.detector.load_model():
                raise RuntimeError("Model loading failed")
            
            if self.config.camera.enabled:
                self.camera = CameraManager(
                    width=self.config.camera.width,
                    height=self.config.camera.height,
                    fps=self.config.camera.fps,
                    format=self.config.camera.format,
                    rotation=self.config.camera.rotation,
                    fallback_usb=self.config.camera.fallback_usb,
                    usb_device_id=self.config.camera.usb_device_id
                )
                if not self.camera.initialize():
                    logger.warning("Camera initialization failed, running in headless mode")
                    self.camera = None
            
            logger.info("Detection service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            self.state = ServiceState.ERROR
            return False
    
    def add_detection_callback(self, callback: Callable[[DetectionEvent], None]):
        """Add a callback to be called on each detection."""
        self._detection_callbacks.append(callback)
    
    def start(self):
        """Start the detection service."""
        if self.state == ServiceState.RUNNING:
            logger.warning("Service already running")
            return
        
        if self.state != ServiceState.STARTING:
            if not self.initialize():
                return
        
        self._stop_event.clear()
        self._start_time = time.time()
        self.state = ServiceState.RUNNING
        
        self._processing_thread = threading.Thread(
            target=self._processing_loop,
            name="DetectionProcessor",
            daemon=True
        )
        self._processing_thread.start()
        
        self._main_thread = threading.Thread(
            target=self._capture_loop,
            name="CaptureLoop",
            daemon=True
        )
        self._main_thread.start()
        
        logger.info("Detection service started")
    
    def stop(self):
        """Stop the detection service gracefully."""
        if self.state == ServiceState.STOPPED:
            return
        
        logger.info("Stopping detection service...")
        self.state = ServiceState.STOPPING
        self._stop_event.set()
        
        timeout = self.config.system.shutdown_timeout_seconds
        
        if self._main_thread and self._main_thread.is_alive():
            self._main_thread.join(timeout=timeout)
        
        if self._processing_thread and self._processing_thread.is_alive():
            self._processing_thread.join(timeout=timeout)
        
        if self.camera:
            self.camera.stop()
        
        if self.detector:
            self.detector.unload()
        
        self.state = ServiceState.STOPPED
        logger.info("Detection service stopped")
    
    def _capture_loop(self):
        """Main capture loop running in separate thread."""
        frame_interval = 1.0 / self.config.camera.fps
        
        while not self._stop_event.is_set():
            loop_start = time.perf_counter()
            
            try:
                if self.camera and self.camera.is_running:
                    frame = self.camera.capture()
                    
                    if frame:
                        self._frame_count += 1
                        self._process_frame(frame)
                else:
                    time.sleep(0.1)
                
            except Exception as e:
                self._error_count += 1
                logger.error(f"Capture loop error: {e}")
                time.sleep(1)
            
            elapsed = time.perf_counter() - loop_start
            sleep_time = max(0, frame_interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _process_frame(self, frame: CameraFrame):
        """Process a single frame for detections."""
        start_time = time.perf_counter()
        
        try:
            detections = self.detector.detect(frame.data)
            
            processing_time = (time.perf_counter() - start_time) * 1000
            
            filtered_detections = self._apply_cooldown(detections)
            
            if filtered_detections:
                event = DetectionEvent(
                    frame=frame,
                    detections=filtered_detections,
                    processing_time_ms=processing_time,
                    timestamp=time.time()
                )
                
                try:
                    self._detection_queue.put_nowait(event)
                except:
                    logger.warning("Detection queue full, dropping event")
                
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
    
    def _apply_cooldown(self, detections: List[Detection]) -> List[Detection]:
        """Filter detections based on cooldown period."""
        cooldown = self.config.alerts.cooldown_seconds
        current_time = time.time()
        filtered = []
        
        for detection in detections:
            class_name = detection.class_name
            last_time = self._last_detection_time.get(class_name, 0)
            
            if current_time - last_time >= cooldown:
                filtered.append(detection)
                self._last_detection_time[class_name] = current_time
        
        return filtered
    
    def _processing_loop(self):
        """Background loop for processing detection events."""
        while not self._stop_event.is_set():
            try:
                event = self._detection_queue.get(timeout=1.0)
                self._handle_detection_event(event)
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Processing loop error: {e}")
    
    def _handle_detection_event(self, event: DetectionEvent):
        """Handle a detection event - save to DB and notify callbacks."""
        for detection in event.detections:
            try:
                image_path = None
                if self.config.storage.images.save_detections and self.image_store:
                    image_path = self.image_store.save_detection_image(
                        image=event.frame.data,
                        detection_id=self._detection_count,
                        class_name=detection.class_name,
                        draw_bbox=detection.bbox
                    )
                
                record = DetectionRecord(
                    id=None,
                    device_id=self.config.device.id,
                    timestamp=detection.timestamp,
                    class_id=detection.class_id,
                    class_name=detection.class_name,
                    confidence=detection.confidence,
                    bbox_x1=detection.bbox[0],
                    bbox_y1=detection.bbox[1],
                    bbox_x2=detection.bbox[2],
                    bbox_y2=detection.bbox[3],
                    image_path=image_path,
                    synced=False,
                    created_at=time.time()
                )
                
                if self.database:
                    record_id = self.database.insert_detection(record)
                    if record_id:
                        self._detection_count += 1
                        logger.info(
                            f"Detection #{record_id}: {detection.class_name} "
                            f"({detection.confidence:.2f}) at {detection.bbox}"
                        )
                
            except Exception as e:
                logger.error(f"Failed to handle detection: {e}")
        
        for callback in self._detection_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Detection callback error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        uptime = time.time() - self._start_time if self._start_time else 0
        
        stats = {
            "state": self.state.value,
            "uptime_seconds": round(uptime, 1),
            "frame_count": self._frame_count,
            "detection_count": self._detection_count,
            "error_count": self._error_count,
            "device_id": self.config.device.id,
            "device_name": self.config.device.name
        }
        
        if self.detector:
            stats["detector"] = self.detector.get_stats()
        
        if self.camera:
            stats["camera"] = self.camera.get_stats()
        
        if self.database:
            stats["database"] = self.database.get_stats()
        
        if self.image_store:
            stats["image_store"] = self.image_store.get_stats()
        
        return stats
    
    def run_forever(self):
        """Run the service until stopped."""
        self.start()
        
        try:
            while self.state == ServiceState.RUNNING:
                time.sleep(1)
                
                if self.image_store:
                    self.image_store.check_storage_limit()
                    
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.stop()
