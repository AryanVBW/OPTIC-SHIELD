"""
Image storage manager for detection snapshots.
Handles saving, compression, and automatic cleanup.
"""

import logging
import time
import io
import os
import base64
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
import threading

import numpy as np

logger = logging.getLogger(__name__)


class ImageStore:
    """
    Manages storage of detection images.
    Optimized for low storage environments with automatic cleanup.
    """
    
    def __init__(
        self,
        base_path: str,
        jpeg_quality: int = 85,
        max_storage_mb: int = 2000,
        cleanup_days: int = 30
    ):
        self.base_path = Path(base_path)
        self.jpeg_quality = jpeg_quality
        self.max_storage_mb = max_storage_mb
        self.cleanup_days = cleanup_days
        self._lock = threading.Lock()
        self._total_saved = 0
    
    def initialize(self) -> bool:
        """Initialize image storage directory."""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Image store initialized: {self.base_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize image store: {e}")
            return False
    
    def save_detection_image(
        self,
        image: np.ndarray,
        detection_id: int,
        class_name: str,
        draw_bbox: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[str]:
        """
        Save a detection image with optional bounding box overlay.
        
        Args:
            image: RGB image as numpy array
            detection_id: Database ID of the detection
            class_name: Detected class name
            draw_bbox: Optional (x1, y1, x2, y2) to draw on image
            
        Returns:
            Relative path to saved image or None on failure
        """
        try:
            from PIL import Image, ImageDraw
            
            date_folder = datetime.now().strftime("%Y-%m-%d")
            save_dir = self.base_path / date_folder
            save_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{timestamp}_{detection_id}_{class_name}.jpg"
            filepath = save_dir / filename
            
            pil_image = Image.fromarray(image)
            
            if draw_bbox:
                draw = ImageDraw.Draw(pil_image)
                x1, y1, x2, y2 = draw_bbox
                draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
                draw.text((x1, y1 - 15), class_name, fill="red")
            
            pil_image.save(filepath, "JPEG", quality=self.jpeg_quality)
            
            with self._lock:
                self._total_saved += 1
            
            relative_path = f"{date_folder}/{filename}"
            logger.debug(f"Saved detection image: {relative_path}")
            return relative_path
            
        except ImportError:
            logger.warning("PIL not available, saving raw image")
            return self._save_raw_image(image, detection_id, class_name)
        except Exception as e:
            logger.error(f"Failed to save detection image: {e}")
            return None
    
    def _save_raw_image(
        self,
        image: np.ndarray,
        detection_id: int,
        class_name: str
    ) -> Optional[str]:
        """Fallback: save image using OpenCV."""
        try:
            import cv2
            
            date_folder = datetime.now().strftime("%Y-%m-%d")
            save_dir = self.base_path / date_folder
            save_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"{timestamp}_{detection_id}_{class_name}.jpg"
            filepath = save_dir / filename
            
            bgr_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(filepath), bgr_image, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
            
            return f"{date_folder}/{filename}"
        except Exception as e:
            logger.error(f"Failed to save raw image: {e}")
            return None
    
    def get_image_base64(
        self,
        image_path: str,
        max_size_kb: int = 100
    ) -> Optional[str]:
        """
        Get image as base64 string, compressed to max size.
        Used for sending images over cellular network.
        """
        try:
            from PIL import Image
            
            full_path = self.base_path / image_path
            if not full_path.exists():
                return None
            
            img = Image.open(full_path)
            
            quality = self.jpeg_quality
            while quality > 10:
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=quality)
                size_kb = buffer.tell() / 1024
                
                if size_kb <= max_size_kb:
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
            logger.error(f"Failed to get image as base64: {e}")
            return None
    
    def cleanup_old_images(self) -> Tuple[int, float]:
        """
        Remove images older than cleanup_days.
        
        Returns:
            Tuple of (files_deleted, mb_freed)
        """
        files_deleted = 0
        bytes_freed = 0
        cutoff_time = time.time() - (self.cleanup_days * 86400)
        
        try:
            for date_folder in self.base_path.iterdir():
                if not date_folder.is_dir():
                    continue
                
                for image_file in date_folder.iterdir():
                    if image_file.stat().st_mtime < cutoff_time:
                        file_size = image_file.stat().st_size
                        image_file.unlink()
                        files_deleted += 1
                        bytes_freed += file_size
                
                if not any(date_folder.iterdir()):
                    date_folder.rmdir()
            
            if files_deleted > 0:
                mb_freed = bytes_freed / (1024 * 1024)
                logger.info(f"Cleaned up {files_deleted} images, freed {mb_freed:.2f} MB")
                return files_deleted, mb_freed
                
        except Exception as e:
            logger.error(f"Failed to cleanup old images: {e}")
        
        return files_deleted, bytes_freed / (1024 * 1024)
    
    def check_storage_limit(self) -> bool:
        """
        Check if storage is approaching limit.
        Triggers cleanup if needed.
        """
        current_size = self.get_storage_size_mb()
        
        if current_size > self.max_storage_mb * 0.9:
            logger.warning(f"Storage at {current_size:.1f}MB, approaching limit of {self.max_storage_mb}MB")
            self.cleanup_old_images()
            return True
        
        return False
    
    def get_storage_size_mb(self) -> float:
        """Get total storage used in MB."""
        total_size = 0
        try:
            for root, dirs, files in os.walk(self.base_path):
                for file in files:
                    filepath = Path(root) / file
                    total_size += filepath.stat().st_size
        except Exception as e:
            logger.error(f"Failed to calculate storage size: {e}")
        
        return total_size / (1024 * 1024)
    
    def get_stats(self) -> dict:
        """Get image store statistics."""
        return {
            "path": str(self.base_path),
            "total_saved": self._total_saved,
            "storage_mb": round(self.get_storage_size_mb(), 2),
            "max_storage_mb": self.max_storage_mb,
            "jpeg_quality": self.jpeg_quality,
            "cleanup_days": self.cleanup_days
        }
