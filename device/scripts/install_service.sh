#!/bin/bash
# Install OPTIC-SHIELD as a systemd service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/optic-shield.service"

echo "Installing OPTIC-SHIELD service..."

# Copy service file
sudo cp "$SERVICE_FILE" /etc/systemd/system/optic-shield.service

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable optic-shield

echo ""
echo "Service installed successfully!"
echo ""
echo "Commands:"
echo "  Start:   sudo systemctl start optic-shield"
echo "  Stop:    sudo systemctl stop optic-shield"
echo "  Status:  sudo systemctl status optic-shield"
echo "  Logs:    journalctl -u optic-shield -f"
echo ""
