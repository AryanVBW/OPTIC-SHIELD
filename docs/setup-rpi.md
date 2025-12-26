# Raspberry Pi 5 Setup Guide

Complete guide for setting up OPTIC-SHIELD on Raspberry Pi 5.

## Hardware Requirements

- **Raspberry Pi 5** (4GB or 8GB RAM)
- **Storage**: 32GB+ microSD or NVMe SSD (recommended)
- **Camera**: Pi Camera Module 3 or compatible USB camera
- **Cellular**: 4G LTE HAT (SIM7600 recommended) for remote deployment
- **Power**: 5V/5A USB-C power supply or solar + battery system

## Software Setup

### 1. Flash Raspberry Pi OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Select **Raspberry Pi OS Lite (64-bit)** - no desktop for better performance
3. Configure SSH, WiFi, and hostname in advanced settings
4. Flash to SD card or SSD

### 2. Initial System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-venv python3-dev git

# Install camera support
sudo apt install -y python3-picamera2 libcamera-apps

# Enable camera
sudo raspi-config
# Navigate to: Interface Options > Camera > Enable
```

### 3. Clone and Setup OPTIC-SHIELD

```bash
# Clone repository
git clone https://github.com/yourusername/OPTIC-SHIELD.git
cd OPTIC-SHIELD/device

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
mkdir -p data/images logs models
```

### 4. Export YOLO Model to NCNN

On your development machine (not the Pi):

```bash
cd OPTIC-SHIELD/device
python scripts/export_model.py
```

Then copy the model to the Pi:

```bash
scp -r models/yolo11n_ncnn_model pi@your-pi-ip:~/OPTIC-SHIELD/device/models/
```

### 5. Configure the Device

```bash
# Copy environment file
cp config/.env.example config/.env

# Edit configuration
nano config/.env
```

Set these values:
```
OPTIC_ENV=production
OPTIC_API_KEY=your_dashboard_api_key
OPTIC_DASHBOARD_URL=https://your-dashboard.vercel.app
OPTIC_DEVICE_SECRET=generate_a_random_string
```

### 6. Test the System

```bash
# Activate virtual environment
source venv/bin/activate

# Run in development mode first
OPTIC_ENV=development python main.py
```

### 7. Setup as System Service

Create a systemd service for automatic startup:

```bash
sudo nano /etc/systemd/system/optic-shield.service
```

Add:
```ini
[Unit]
Description=OPTIC-SHIELD Wildlife Detection Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/OPTIC-SHIELD/device
Environment=OPTIC_ENV=production
ExecStart=/home/pi/OPTIC-SHIELD/device/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable optic-shield
sudo systemctl start optic-shield

# Check status
sudo systemctl status optic-shield

# View logs
journalctl -u optic-shield -f
```

## Performance Optimization

### 1. Overclock (Optional)

Edit `/boot/firmware/config.txt`:
```
arm_freq=2800
gpu_freq=900
over_voltage=4
```

### 2. Disable Unnecessary Services

```bash
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon
```

### 3. Use SSD Storage

For 24/7 operation, use NVMe SSD instead of SD card:
- Get an NVMe HAT for Pi 5
- Flash OS to SSD
- Boot from SSD

## Troubleshooting

### Camera Not Detected

```bash
# Check camera connection
libcamera-hello

# Check if camera is enabled
vcgencmd get_camera
```

### High Memory Usage

Reduce image resolution in config:
```yaml
camera:
  resolution:
    width: 480
    height: 360
```

### Model Loading Slow

Ensure NCNN model is being used:
```yaml
detection:
  use_ncnn: true
```

## Monitoring

View real-time logs:
```bash
tail -f ~/OPTIC-SHIELD/device/logs/optic-shield.log
```

Check system resources:
```bash
htop
vcgencmd measure_temp
```
