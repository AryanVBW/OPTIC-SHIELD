"""
SQLite database for storing detections and device state.
Optimized for low-resource environments with automatic cleanup.
"""

import logging
import sqlite3
import time
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DetectionRecord:
    """Database record for a detection."""
    id: Optional[int]
    device_id: str
    timestamp: float
    class_id: int
    class_name: str
    confidence: float
    bbox_x1: int
    bbox_y1: int
    bbox_x2: int
    bbox_y2: int
    image_path: Optional[str]
    synced: bool
    created_at: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "device_id": self.device_id,
            "timestamp": self.timestamp,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bbox": [self.bbox_x1, self.bbox_y1, self.bbox_x2, self.bbox_y2],
            "image_path": self.image_path,
            "synced": self.synced,
            "created_at": self.created_at
        }


class DetectionDatabase:
    """
    SQLite database manager for detection records.
    Thread-safe with connection pooling.
    """
    
    def __init__(self, db_path: str, max_size_mb: int = 500):
        self.db_path = Path(db_path)
        self.max_size_mb = max_size_mb
        self._lock = threading.Lock()
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize database and create tables."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self._get_connection() as conn:
                self._create_tables(conn)
                self._create_indexes(conn)
            
            self._initialized = True
            logger.info(f"Database initialized: {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper cleanup."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            isolation_level=None
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-2000")
        try:
            yield conn
        finally:
            conn.close()
    
    def _create_tables(self, conn: sqlite3.Connection):
        """Create database tables."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                class_id INTEGER NOT NULL,
                class_name TEXT NOT NULL,
                confidence REAL NOT NULL,
                bbox_x1 INTEGER NOT NULL,
                bbox_y1 INTEGER NOT NULL,
                bbox_x2 INTEGER NOT NULL,
                bbox_y2 INTEGER NOT NULL,
                image_path TEXT,
                synced INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS device_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detection_id INTEGER NOT NULL,
                payload TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                last_attempt REAL,
                created_at REAL NOT NULL,
                FOREIGN KEY (detection_id) REFERENCES detections(id)
            )
        """)
    
    def _create_indexes(self, conn: sqlite3.Connection):
        """Create database indexes for performance."""
        conn.execute("CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_detections_synced ON detections(synced)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_detections_class ON detections(class_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_queue_attempts ON sync_queue(attempts)")
    
    def insert_detection(self, record: DetectionRecord) -> Optional[int]:
        """Insert a detection record and return its ID."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute("""
                        INSERT INTO detections 
                        (device_id, timestamp, class_id, class_name, confidence,
                         bbox_x1, bbox_y1, bbox_x2, bbox_y2, image_path, synced, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record.device_id,
                        record.timestamp,
                        record.class_id,
                        record.class_name,
                        record.confidence,
                        record.bbox_x1,
                        record.bbox_y1,
                        record.bbox_x2,
                        record.bbox_y2,
                        record.image_path,
                        1 if record.synced else 0,
                        record.created_at
                    ))
                    return cursor.lastrowid
            except Exception as e:
                logger.error(f"Failed to insert detection: {e}")
                return None
    
    def get_unsynced_detections(self, limit: int = 100) -> List[DetectionRecord]:
        """Get detections that haven't been synced to dashboard."""
        records = []
        try:
            with self._get_connection() as conn:
                rows = conn.execute("""
                    SELECT * FROM detections 
                    WHERE synced = 0 
                    ORDER BY timestamp ASC 
                    LIMIT ?
                """, (limit,)).fetchall()
                
                for row in rows:
                    records.append(self._row_to_record(row))
        except Exception as e:
            logger.error(f"Failed to get unsynced detections: {e}")
        return records
    
    def mark_synced(self, detection_ids: List[int]):
        """Mark detections as synced."""
        if not detection_ids:
            return
        
        with self._lock:
            try:
                with self._get_connection() as conn:
                    placeholders = ",".join("?" * len(detection_ids))
                    conn.execute(f"""
                        UPDATE detections SET synced = 1 
                        WHERE id IN ({placeholders})
                    """, detection_ids)
            except Exception as e:
                logger.error(f"Failed to mark detections as synced: {e}")
    
    def get_recent_detections(self, hours: int = 24, limit: int = 100) -> List[DetectionRecord]:
        """Get recent detections within specified hours."""
        records = []
        cutoff = time.time() - (hours * 3600)
        
        try:
            with self._get_connection() as conn:
                rows = conn.execute("""
                    SELECT * FROM detections 
                    WHERE timestamp > ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (cutoff, limit)).fetchall()
                
                for row in rows:
                    records.append(self._row_to_record(row))
        except Exception as e:
            logger.error(f"Failed to get recent detections: {e}")
        return records
    
    def get_detection_count(self, hours: int = 24) -> int:
        """Get count of detections in specified time period."""
        cutoff = time.time() - (hours * 3600)
        try:
            with self._get_connection() as conn:
                result = conn.execute("""
                    SELECT COUNT(*) FROM detections WHERE timestamp > ?
                """, (cutoff,)).fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Failed to get detection count: {e}")
            return 0
    
    def get_class_distribution(self, hours: int = 24) -> Dict[str, int]:
        """Get distribution of detected classes."""
        cutoff = time.time() - (hours * 3600)
        distribution = {}
        
        try:
            with self._get_connection() as conn:
                rows = conn.execute("""
                    SELECT class_name, COUNT(*) as count 
                    FROM detections 
                    WHERE timestamp > ?
                    GROUP BY class_name
                    ORDER BY count DESC
                """, (cutoff,)).fetchall()
                
                for row in rows:
                    distribution[row['class_name']] = row['count']
        except Exception as e:
            logger.error(f"Failed to get class distribution: {e}")
        return distribution
    
    def set_state(self, key: str, value: str):
        """Set a device state value."""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO device_state (key, value, updated_at)
                        VALUES (?, ?, ?)
                    """, (key, value, time.time()))
            except Exception as e:
                logger.error(f"Failed to set state {key}: {e}")
    
    def get_state(self, key: str, default: str = "") -> str:
        """Get a device state value."""
        try:
            with self._get_connection() as conn:
                row = conn.execute("""
                    SELECT value FROM device_state WHERE key = ?
                """, (key,)).fetchone()
                return row['value'] if row else default
        except Exception as e:
            logger.error(f"Failed to get state {key}: {e}")
            return default
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """Delete records older than specified days."""
        cutoff = time.time() - (days * 86400)
        deleted = 0
        
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.execute("""
                        DELETE FROM detections WHERE timestamp < ? AND synced = 1
                    """, (cutoff,))
                    deleted = cursor.rowcount
                    
                    conn.execute("VACUUM")
                    
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} old detection records")
            except Exception as e:
                logger.error(f"Failed to cleanup old records: {e}")
        
        return deleted
    
    def get_database_size_mb(self) -> float:
        """Get current database size in MB."""
        try:
            if self.db_path.exists():
                return self.db_path.stat().st_size / (1024 * 1024)
        except Exception:
            pass
        return 0.0
    
    def _row_to_record(self, row: sqlite3.Row) -> DetectionRecord:
        """Convert database row to DetectionRecord."""
        return DetectionRecord(
            id=row['id'],
            device_id=row['device_id'],
            timestamp=row['timestamp'],
            class_id=row['class_id'],
            class_name=row['class_name'],
            confidence=row['confidence'],
            bbox_x1=row['bbox_x1'],
            bbox_y1=row['bbox_y1'],
            bbox_x2=row['bbox_x2'],
            bbox_y2=row['bbox_y2'],
            image_path=row['image_path'],
            synced=bool(row['synced']),
            created_at=row['created_at']
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return {
            "initialized": self._initialized,
            "path": str(self.db_path),
            "size_mb": round(self.get_database_size_mb(), 2),
            "max_size_mb": self.max_size_mb,
            "total_detections": self.get_detection_count(hours=24*365),
            "unsynced_count": len(self.get_unsynced_detections(limit=1000))
        }
