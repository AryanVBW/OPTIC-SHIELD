"""
System resource monitoring for Raspberry Pi.
Tracks CPU, memory, temperature, and storage.
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SystemStats:
    """System resource statistics."""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    temperature_celsius: Optional[float]
    disk_percent: float
    disk_used_gb: float
    disk_free_gb: float
    uptime_seconds: float


class SystemMonitor:
    """
    Monitors system resources on Raspberry Pi.
    Provides alerts when resources are constrained.
    """
    
    def __init__(
        self,
        max_memory_mb: int = 512,
        max_cpu_percent: int = 80,
        check_interval: int = 30
    ):
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.check_interval = check_interval
        
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._last_stats: Optional[SystemStats] = None
        self._alert_callbacks: list = []
        self._start_time = time.time()
    
    def start(self):
        """Start background monitoring."""
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="SystemMonitor",
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("System monitor started")
    
    def stop(self):
        """Stop background monitoring."""
        self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        logger.info("System monitor stopped")
    
    def add_alert_callback(self, callback: Callable[[str, Any], None]):
        """Add callback for resource alerts."""
        self._alert_callbacks.append(callback)
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while not self._stop_event.is_set():
            try:
                stats = self.get_stats()
                self._last_stats = stats
                self._check_thresholds(stats)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
            
            self._stop_event.wait(self.check_interval)
    
    def get_stats(self) -> SystemStats:
        """Get current system statistics."""
        cpu_percent = self._get_cpu_percent()
        memory = self._get_memory_info()
        temperature = self._get_temperature()
        disk = self._get_disk_info()
        uptime = time.time() - self._start_time
        
        return SystemStats(
            cpu_percent=cpu_percent,
            memory_percent=memory.get("percent", 0),
            memory_used_mb=memory.get("used_mb", 0),
            memory_available_mb=memory.get("available_mb", 0),
            temperature_celsius=temperature,
            disk_percent=disk.get("percent", 0),
            disk_used_gb=disk.get("used_gb", 0),
            disk_free_gb=disk.get("free_gb", 0),
            uptime_seconds=uptime
        )
    
    def _get_cpu_percent(self) -> float:
        """Get CPU usage percentage."""
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
                fields = line.split()
                idle = int(fields[4])
                total = sum(int(x) for x in fields[1:])
                
                if not hasattr(self, "_last_cpu"):
                    self._last_cpu = (idle, total)
                    return 0.0
                
                last_idle, last_total = self._last_cpu
                idle_delta = idle - last_idle
                total_delta = total - last_total
                
                self._last_cpu = (idle, total)
                
                if total_delta == 0:
                    return 0.0
                
                return round((1 - idle_delta / total_delta) * 100, 1)
        except Exception:
            return 0.0
    
    def _get_memory_info(self) -> Dict[str, float]:
        """Get memory usage information."""
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            
            mem_info = {}
            for line in lines:
                parts = line.split()
                key = parts[0].rstrip(":")
                value = int(parts[1])
                mem_info[key] = value
            
            total = mem_info.get("MemTotal", 0) / 1024
            available = mem_info.get("MemAvailable", 0) / 1024
            used = total - available
            percent = (used / total * 100) if total > 0 else 0
            
            return {
                "total_mb": round(total, 1),
                "used_mb": round(used, 1),
                "available_mb": round(available, 1),
                "percent": round(percent, 1)
            }
        except Exception:
            return {"total_mb": 0, "used_mb": 0, "available_mb": 0, "percent": 0}
    
    def _get_temperature(self) -> Optional[float]:
        """Get CPU temperature (Raspberry Pi specific)."""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = int(f.read().strip()) / 1000.0
                return round(temp, 1)
        except Exception:
            return None
    
    def _get_disk_info(self) -> Dict[str, float]:
        """Get disk usage information."""
        try:
            import os
            stat = os.statvfs("/")
            
            total = stat.f_blocks * stat.f_frsize / (1024 ** 3)
            free = stat.f_bavail * stat.f_frsize / (1024 ** 3)
            used = total - free
            percent = (used / total * 100) if total > 0 else 0
            
            return {
                "total_gb": round(total, 2),
                "used_gb": round(used, 2),
                "free_gb": round(free, 2),
                "percent": round(percent, 1)
            }
        except Exception:
            return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0}
    
    def _check_thresholds(self, stats: SystemStats):
        """Check resource thresholds and trigger alerts."""
        if stats.memory_used_mb > self.max_memory_mb:
            self._trigger_alert(
                "memory_high",
                f"Memory usage {stats.memory_used_mb:.0f}MB exceeds limit {self.max_memory_mb}MB"
            )
        
        if stats.cpu_percent > self.max_cpu_percent:
            self._trigger_alert(
                "cpu_high",
                f"CPU usage {stats.cpu_percent:.1f}% exceeds limit {self.max_cpu_percent}%"
            )
        
        if stats.temperature_celsius and stats.temperature_celsius > 80:
            self._trigger_alert(
                "temperature_high",
                f"Temperature {stats.temperature_celsius:.1f}°C is critically high"
            )
        
        if stats.disk_percent > 90:
            self._trigger_alert(
                "disk_high",
                f"Disk usage {stats.disk_percent:.1f}% is critically high"
            )
    
    def _trigger_alert(self, alert_type: str, message: str):
        """Trigger resource alert."""
        logger.warning(f"System alert [{alert_type}]: {message}")
        
        for callback in self._alert_callbacks:
            try:
                callback(alert_type, message)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def get_stats_dict(self) -> Dict[str, Any]:
        """Get stats as dictionary."""
        stats = self._last_stats or self.get_stats()
        return {
            "cpu_percent": stats.cpu_percent,
            "memory_percent": stats.memory_percent,
            "memory_used_mb": stats.memory_used_mb,
            "memory_available_mb": stats.memory_available_mb,
            "temperature_celsius": stats.temperature_celsius,
            "disk_percent": stats.disk_percent,
            "disk_used_gb": stats.disk_used_gb,
            "disk_free_gb": stats.disk_free_gb,
            "uptime_seconds": stats.uptime_seconds
        }
