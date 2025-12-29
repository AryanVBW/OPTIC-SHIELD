#!/usr/bin/env python3
"""
Simple camera detection test script for debugging.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.camera import CameraDetector, CameraManager
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_camera_detection():
    """Test camera detection."""
    print("=" * 60)
    print("Camera Detection Test")
    print("=" * 60)
    
    # Detect all cameras
    print("\n1. Detecting all cameras...")
    cameras = CameraDetector.detect_all()
    
    for i, cam in enumerate(cameras):
        print(f"\nCamera {i}:")
        print(f"  Available: {cam.available}")
        print(f"  Type: {cam.camera_type.value}")
        print(f"  Device Path: {cam.device_path}")
        print(f"  Device Name: {cam.device_name}")
        print(f"  Capabilities: {cam.capabilities}")
        if cam.error:
            print(f"  Error: {cam.error}")
    
    # Get best camera
    print("\n2. Getting best available camera...")
    best = CameraDetector.get_best_camera()
    
    if best:
        print(f"  Best camera: {best.device_name} ({best.camera_type.value})")
        print(f"  Device path: {best.device_path}")
    else:
        print("  No camera available!")
        return False
    
    # Try to initialize camera manager
    print("\n3. Initializing CameraManager...")
    camera = CameraManager(
        width=640,
        height=480,
        fps=10,
        fallback_usb=True,
        usb_device_id=0
    )
    
    if camera.initialize():
        print("  ✓ Camera initialized successfully!")
        
        # Get camera info
        info = camera.get_camera_info()
        print(f"\n4. Camera Info:")
        print(f"  Type: {info.get('type')}")
        print(f"  Name: {info.get('name')}")
        print(f"  Model: {info.get('model')}")
        print(f"  Device Path: {info.get('device_path')}")
        print(f"  Resolution: {info.get('resolution')}")
        print(f"  FPS: {info.get('fps')}")
        print(f"  Status: {info.get('status')}")
        
        # Try to capture a frame
        print("\n5. Testing frame capture...")
        frame = camera.capture()
        
        if frame:
            print(f"  ✓ Frame captured successfully!")
            print(f"    Size: {frame.width}x{frame.height}")
            print(f"    Camera Type: {frame.camera_type.value}")
        else:
            print("  ✗ Frame capture failed!")
        
        camera.stop()
        return True
    else:
        print("  ✗ Camera initialization failed!")
        return False

if __name__ == "__main__":
    try:
        success = test_camera_detection()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
