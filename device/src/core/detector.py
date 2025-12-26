"""
YOLO-based wildlife detector optimized for Raspberry Pi 5.
Supports NCNN format for maximum performance on ARM architecture.
"""

import logging
import time
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
import threading

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """Represents a single detection result."""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bbox": list(self.bbox),
            "timestamp": self.timestamp
        }


class WildlifeDetector:
    """
    Wildlife detection engine using YOLO11n.
    Optimized for Raspberry Pi 5 with NCNN backend.
    """
    
    COCO_ANIMAL_CLASSES = {
        14: "bird",
        15: "cat", 
        16: "dog",
        17: "horse",
        18: "sheep",
        19: "cow",
        20: "elephant",
        21: "bear",
        22: "zebra",
        23: "giraffe"
    }
    
    def __init__(
        self,
        model_path: str,
        fallback_path: str = "",
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        target_classes: Optional[List[int]] = None,
        use_ncnn: bool = True,
        num_threads: int = 4
    ):
        self.model_path = Path(model_path)
        self.fallback_path = Path(fallback_path) if fallback_path else None
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.target_classes = target_classes or list(self.COCO_ANIMAL_CLASSES.keys())
        self.use_ncnn = use_ncnn
        self.num_threads = num_threads
        
        self.model = None
        self.model_loaded = False
        self._lock = threading.Lock()
        self._inference_times: List[float] = []
        self._max_inference_history = 100
        
    def load_model(self) -> bool:
        """Load the YOLO model with fallback support."""
        try:
            from ultralytics import YOLO
            
            model_to_load = None
            
            if self.model_path.exists():
                model_to_load = str(self.model_path)
                logger.info(f"Loading model from: {self.model_path}")
            elif self.fallback_path and self.fallback_path.exists():
                model_to_load = str(self.fallback_path)
                logger.warning(f"Primary model not found, using fallback: {self.fallback_path}")
                self.use_ncnn = False
            else:
                logger.info("No local model found, downloading yolo11n.pt...")
                model_to_load = "yolo11n.pt"
                self.use_ncnn = False
            
            self.model = YOLO(model_to_load)
            self.model_loaded = True
            
            self._warmup()
            
            logger.info(f"Model loaded successfully (NCNN: {self.use_ncnn})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.model_loaded = False
            return False
    
    def _warmup(self):
        """Warm up the model with a dummy inference."""
        if not self.model:
            return
        
        try:
            dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
            self.model(dummy_image, verbose=False)
            logger.debug("Model warmup completed")
        except Exception as e:
            logger.warning(f"Model warmup failed: {e}")
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Run detection on a single frame.
        
        Args:
            frame: BGR or RGB image as numpy array
            
        Returns:
            List of Detection objects for target classes
        """
        if not self.model_loaded or self.model is None:
            logger.warning("Model not loaded, skipping detection")
            return []
        
        detections = []
        start_time = time.perf_counter()
        
        try:
            with self._lock:
                results = self.model(
                    frame,
                    conf=self.confidence_threshold,
                    iou=self.iou_threshold,
                    verbose=False
                )
            
            inference_time = (time.perf_counter() - start_time) * 1000
            self._record_inference_time(inference_time)
            
            if results and len(results) > 0:
                result = results[0]
                
                if result.boxes is not None:
                    for box in result.boxes:
                        class_id = int(box.cls[0])
                        
                        if class_id not in self.target_classes:
                            continue
                        
                        confidence = float(box.conf[0])
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        
                        class_name = self.COCO_ANIMAL_CLASSES.get(
                            class_id, 
                            self.model.names.get(class_id, f"class_{class_id}")
                        )
                        
                        detection = Detection(
                            class_id=class_id,
                            class_name=class_name,
                            confidence=confidence,
                            bbox=(x1, y1, x2, y2),
                            timestamp=time.time()
                        )
                        detections.append(detection)
            
            logger.debug(f"Detection completed in {inference_time:.1f}ms, found {len(detections)} animals")
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
        
        return detections
    
    def _record_inference_time(self, time_ms: float):
        """Record inference time for performance monitoring."""
        self._inference_times.append(time_ms)
        if len(self._inference_times) > self._max_inference_history:
            self._inference_times.pop(0)
    
    def get_average_inference_time(self) -> float:
        """Get average inference time in milliseconds."""
        if not self._inference_times:
            return 0.0
        return sum(self._inference_times) / len(self._inference_times)
    
    def get_fps(self) -> float:
        """Get estimated FPS based on inference time."""
        avg_time = self.get_average_inference_time()
        if avg_time <= 0:
            return 0.0
        return 1000.0 / avg_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        return {
            "model_loaded": self.model_loaded,
            "use_ncnn": self.use_ncnn,
            "avg_inference_ms": round(self.get_average_inference_time(), 2),
            "estimated_fps": round(self.get_fps(), 2),
            "target_classes": self.target_classes,
            "confidence_threshold": self.confidence_threshold
        }
    
    def unload(self):
        """Unload model to free memory."""
        with self._lock:
            self.model = None
            self.model_loaded = False
        logger.info("Model unloaded")
