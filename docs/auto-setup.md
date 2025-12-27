# OPTIC-SHIELD Auto Setup Guide

Complete documentation for the automated setup system.

## Overview

The auto-setup system provides one-command installation with:
- **Platform Detection**: Automatically detects OS, architecture, and hardware
- **Dependency Installation**: Platform-specific package installation
- **Validation**: 19-point checklist to verify everything works
- **Testing**: Automated tests with "Tested OK" report

## Quick Start

```bash
cd OPTIC-SHIELD/device
bash scripts/auto_setup.sh
```

## Setup Commands

| Command | Description |
|---------|-------------|
| `auto_setup.sh` | Full installation with validation |
| `auto_setup.sh --validate` | Only run validation checks |
| `auto_setup.sh --info` | Show platform information |
| `auto_setup.sh --service` | Install systemd service |
| `auto_setup.sh --all` | Full install + service + tests |

## Platform Support

| Platform | Auto-Install | Systemd Service | NCNN Support |
|----------|--------------|-----------------|--------------|
| Raspberry Pi 5 | ✓ | ✓ | ✓ |
| Raspberry Pi 4 | ✓ | ✓ | ✓ |
| Debian/Ubuntu | ✓ | ✓ | ✓ |
| macOS (dev) | ✓ | ✗ | ✓ (x86_64) |
| Windows | ✗ | ✗ | ✓ |

## Validation Checklist

The validation script checks 19 components:

1. **Python Version** - Python 3.10+
2. **Virtual Environment** - venv exists and valid
3. **Core Dependencies** - ultralytics, numpy, Pillow, PyYAML
4. **OpenCV** - opencv-python-headless
5. **Camera Module** - picamera2 (RPi) or OpenCV
6. **GPIO Module** - RPi.GPIO (RPi only)
7. **Config Files** - config.yaml present
8. **Data Directory** - data/ with write access
9. **Logs Directory** - logs/ with write access
10. **Models Directory** - models/ exists
11. **YOLO Model** - Model file present or auto-download
12. **Database** - SQLite connection test
13. **Camera Hardware** - Camera detection
14. **Model Load** - YOLO model loads successfully
15. **Detection** - Inference test on dummy image
16. **Storage** - Read/write test
17. **Systemd Service** - Service installed (Linux)
18. **User Permissions** - video/gpio groups (RPi)
19. **Network** - Internet connectivity (optional)

Run validation:
```bash
python scripts/validate_setup.py
python scripts/validate_setup.py --json  # JSON output
```

## Running Tests

```bash
python scripts/run_tests.py
python scripts/run_tests.py --report test_report.json
```

## Expected Output

Successful setup produces:

```
╔══════════════════════════════════════════════════════════════╗
║                OPTIC-SHIELD VALIDATION REPORT                ║
╠══════════════════════════════════════════════════════════════╣
║  Platform: Raspberry Pi OS                                   ║
║  Python:   3.11.2                                            ║
║  Arch:     arm64                                             ║
╠══════════════════════════════════════════════════════════════╣
║  Validation Results:                                         ║
║  ✓ Python Version          3.11.2                            ║
║  ✓ Virtual Environment     Found at venv/                    ║
║  ...                                                         ║
╠══════════════════════════════════════════════════════════════╣
║   ✅ TESTED OK - Ready to use!                               ║
╚══════════════════════════════════════════════════════════════╝
```

## Troubleshooting

### Missing Groups
```bash
# Add user to required groups
sudo usermod -aG video,gpio,i2c $USER
# Log out and back in
```

### Camera Not Detected
```bash
# Enable camera in raspi-config
sudo raspi-config
# Interface Options > Camera > Enable

# Test camera
libcamera-hello
```

### Model Download Failed
```bash
# Manually download model
cd models
wget https://github.com/ultralytics/assets/releases/download/v8.1.0/yolo11n.pt
```
