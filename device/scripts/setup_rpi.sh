#!/bin/bash
# ============================================================================
# OPTIC-SHIELD Raspberry Pi Setup Script (DEPRECATED)
# ============================================================================
#
# This script is deprecated. Please use auto_setup.sh instead.
# Keeping for backward compatibility.
#
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ⚠️  DEPRECATION NOTICE                                       ║"
echo "║                                                              ║"
echo "║  This script (setup_rpi.sh) is deprecated.                  ║"
echo "║  Please use auto_setup.sh instead:                          ║"
echo "║                                                              ║"
echo "║    bash scripts/auto_setup.sh                               ║"
echo "║                                                              ║"
echo "║  auto_setup.sh provides:                                    ║"
echo "║    • Auto platform detection                                ║"
echo "║    • Comprehensive validation                               ║"
echo "║    • Testing and 'Tested OK' report                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

read -p "Run auto_setup.sh instead? [Y/n] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    exec "$SCRIPT_DIR/auto_setup.sh" "$@"
fi

# Legacy setup (if user declines redirect)
echo "Running legacy setup..."

echo "=========================================="
echo "OPTIC-SHIELD Raspberry Pi Setup"
echo "=========================================="

# Update system
echo "[1/6] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python dependencies
echo "[2/6] Installing Python and pip..."
sudo apt install -y python3-pip python3-venv python3-dev

# Install camera dependencies
echo "[3/6] Installing camera dependencies..."
sudo apt install -y python3-picamera2 libcamera-apps

# Install OpenCV dependencies
echo "[4/6] Installing OpenCV dependencies..."
sudo apt install -y libopencv-dev python3-opencv

# Create virtual environment
echo "[5/6] Creating Python virtual environment..."
cd "$(dirname "$0")/.."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "[6/6] Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Create data directories
mkdir -p data/images logs models

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Copy your NCNN model to: models/yolo11n_ncnn_model/"
echo "2. Configure: cp config/.env.example config/.env"
echo "3. Edit config/.env with your settings"
echo "4. Run: python main.py"
echo ""
echo "TIP: Run 'python scripts/validate_setup.py' to verify setup"
echo ""

