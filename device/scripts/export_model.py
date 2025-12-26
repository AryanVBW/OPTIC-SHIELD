#!/usr/bin/env python3
"""
Export YOLO model to NCNN format for Raspberry Pi deployment.
Run this script on your development machine before deploying to Pi.
"""

import os
import sys
from pathlib import Path

def export_to_ncnn():
    """Export YOLO11n to NCNN format."""
    try:
        from ultralytics import YOLO
        
        print("=" * 60)
        print("OPTIC-SHIELD Model Export Tool")
        print("=" * 60)
        
        base_path = Path(__file__).parent.parent
        models_dir = base_path / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        
        print("\n[1/3] Loading YOLO11n model...")
        model = YOLO("yolo11n.pt")
        
        print("\n[2/3] Exporting to NCNN format...")
        print("This may take a few minutes...")
        
        ncnn_path = model.export(format="ncnn")
        
        print(f"\n[3/3] Model exported successfully!")
        print(f"NCNN model saved to: {ncnn_path}")
        
        target_path = models_dir / "yolo11n_ncnn_model"
        if Path(ncnn_path).exists() and not target_path.exists():
            import shutil
            shutil.move(ncnn_path, target_path)
            print(f"Moved to: {target_path}")
        
        pt_path = models_dir / "yolo11n.pt"
        if not pt_path.exists():
            import shutil
            shutil.copy("yolo11n.pt", pt_path)
            print(f"Copied PyTorch model to: {pt_path}")
        
        print("\n" + "=" * 60)
        print("Export complete! You can now deploy to Raspberry Pi.")
        print("=" * 60)
        
    except ImportError:
        print("Error: ultralytics package not installed")
        print("Install with: pip install ultralytics")
        sys.exit(1)
    except Exception as e:
        print(f"Error during export: {e}")
        sys.exit(1)


if __name__ == "__main__":
    export_to_ncnn()
