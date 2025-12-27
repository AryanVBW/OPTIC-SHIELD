#!/bin/bash
# OPTIC-SHIELD Dependency Installation Library
# Platform-specific dependency installation

# Source platform detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/platform_detect.sh"

# ============================================================================
# Package Managers
# ============================================================================

install_apt_packages() {
    local packages=("$@")
    
    echo -e "${BLUE}Installing apt packages: ${packages[*]}${NC}"
    sudo apt-get update -qq
    sudo apt-get install -y "${packages[@]}"
}

install_brew_packages() {
    local packages=("$@")
    
    if ! command -v brew &>/dev/null; then
        echo -e "${YELLOW}Homebrew not found, skipping macOS packages${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Installing Homebrew packages: ${packages[*]}${NC}"
    brew install "${packages[@]}"
}

# ============================================================================
# System Dependencies
# ============================================================================

install_system_deps() {
    local os_type
    os_type=$(detect_os)
    
    echo -e "\n${BLUE}[1/4] Installing system dependencies...${NC}"
    
    case "$os_type" in
        raspberry_pi)
            install_rpi_system_deps
            ;;
        linux)
            install_linux_system_deps
            ;;
        macos)
            install_macos_system_deps
            ;;
        *)
            echo -e "${YELLOW}⚠ Unsupported OS for auto-install${NC}"
            return 1
            ;;
    esac
}

install_rpi_system_deps() {
    echo "Installing Raspberry Pi dependencies..."
    
    # Update system
    sudo apt-get update -qq
    sudo apt-get upgrade -y
    
    # Core dependencies
    install_apt_packages \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        curl \
        wget
    
    # Camera support
    install_apt_packages \
        python3-picamera2 \
        libcamera-apps \
        libcamera-dev
    
    # OpenCV dependencies
    install_apt_packages \
        libopencv-dev \
        python3-opencv
    
    # GPIO support
    install_apt_packages \
        python3-rpi.gpio \
        python3-gpiozero
    
    echo -e "${GREEN}✓ Raspberry Pi dependencies installed${NC}"
}

install_linux_system_deps() {
    echo "Installing Linux dependencies..."
    
    # Detect package manager
    if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq
        install_apt_packages \
            python3-pip \
            python3-venv \
            python3-dev \
            git \
            curl \
            libopencv-dev \
            python3-opencv
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y \
            python3-pip \
            python3-devel \
            git \
            curl \
            opencv \
            python3-opencv
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm \
            python-pip \
            git \
            curl \
            opencv \
            python-opencv
    else
        echo -e "${YELLOW}⚠ Unknown package manager, please install dependencies manually${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ Linux dependencies installed${NC}"
}

install_macos_system_deps() {
    echo "Installing macOS dependencies..."
    
    # Check for Homebrew
    if ! command -v brew &>/dev/null; then
        echo -e "${YELLOW}Installing Homebrew...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    # Install packages
    install_brew_packages python@3.11 opencv
    
    echo -e "${GREEN}✓ macOS dependencies installed${NC}"
}

# ============================================================================
# Python Environment
# ============================================================================

setup_python_venv() {
    local install_dir="$1"
    local venv_dir="$install_dir/venv"
    local python_cmd
    
    echo -e "\n${BLUE}[2/4] Setting up Python virtual environment...${NC}"
    
    python_cmd=$(detect_python)
    if [ -z "$python_cmd" ]; then
        echo -e "${RED}✗ Python 3.10+ not found${NC}"
        return 1
    fi
    
    # Create venv if it doesn't exist
    if [ ! -d "$venv_dir" ]; then
        echo "Creating virtual environment at $venv_dir"
        "$python_cmd" -m venv "$venv_dir"
    else
        echo "Virtual environment already exists"
    fi
    
    # Activate and upgrade pip
    source "$venv_dir/bin/activate"
    pip install --upgrade pip setuptools wheel
    
    echo -e "${GREEN}✓ Virtual environment ready${NC}"
}

install_python_packages() {
    local install_dir="$1"
    local venv_dir="$install_dir/venv"
    local os_type
    
    echo -e "\n${BLUE}[3/4] Installing Python packages...${NC}"
    
    os_type=$(detect_os)
    
    # Activate venv
    source "$venv_dir/bin/activate"
    
    # Install from requirements.txt
    if [ -f "$install_dir/requirements.txt" ]; then
        pip install -r "$install_dir/requirements.txt"
    fi
    
    # Install platform-specific packages
    case "$os_type" in
        raspberry_pi)
            # picamera2 is usually installed system-wide
            pip install RPi.GPIO 2>/dev/null || true
            ;;
    esac
    
    # Verify core packages
    echo "Verifying installed packages..."
    python -c "import ultralytics; print(f'  ultralytics: {ultralytics.__version__}')" 2>/dev/null || echo "  ⚠ ultralytics not installed"
    python -c "import numpy; print(f'  numpy: {numpy.__version__}')" 2>/dev/null || echo "  ⚠ numpy not installed"
    python -c "import cv2; print(f'  opencv: {cv2.__version__}')" 2>/dev/null || echo "  ⚠ opencv not installed"
    python -c "import yaml; print(f'  PyYAML: installed')" 2>/dev/null || echo "  ⚠ PyYAML not installed"
    
    echo -e "${GREEN}✓ Python packages installed${NC}"
}

# ============================================================================
# Directory Setup
# ============================================================================

setup_directories() {
    local install_dir="$1"
    local user
    user=$(detect_current_user)
    
    echo -e "\n${BLUE}[4/4] Setting up directories...${NC}"
    
    # Create required directories
    mkdir -p "$install_dir/data/images"
    mkdir -p "$install_dir/logs"
    mkdir -p "$install_dir/models"
    mkdir -p "$install_dir/config"
    
    # Set ownership if running as root
    if [ "$(id -u)" -eq 0 ] && [ -n "$user" ] && [ "$user" != "root" ]; then
        chown -R "$user:$user" "$install_dir/data"
        chown -R "$user:$user" "$install_dir/logs"
        chown -R "$user:$user" "$install_dir/models"
    fi
    
    echo -e "  ${GREEN}✓${NC} data/images"
    echo -e "  ${GREEN}✓${NC} logs"
    echo -e "  ${GREEN}✓${NC} models"
    echo -e "  ${GREEN}✓${NC} config"
    
    echo -e "${GREEN}✓ Directories created${NC}"
}

# ============================================================================
# Service Installation (Linux/systemd)
# ============================================================================

install_systemd_service() {
    local install_dir="$1"
    local user
    user=$(detect_current_user)
    
    local os_type
    os_type=$(detect_os)
    
    if [ "$os_type" != "raspberry_pi" ] && [ "$os_type" != "linux" ]; then
        echo -e "${YELLOW}⚠ Systemd service only available on Linux${NC}"
        return 1
    fi
    
    if ! command -v systemctl &>/dev/null; then
        echo -e "${YELLOW}⚠ systemctl not found, skipping service installation${NC}"
        return 1
    fi
    
    echo -e "\n${BLUE}Installing systemd service...${NC}"
    
    # Create service file
    local service_file="/etc/systemd/system/optic-shield.service"
    
    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=OPTIC-SHIELD Wildlife Detection Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=$user
Group=$user
WorkingDirectory=$install_dir
Environment=OPTIC_ENV=production
EnvironmentFile=-$install_dir/config/.env
ExecStart=$install_dir/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Resource limits
MemoryMax=1G
CPUQuota=90%

# Watchdog
WatchdogSec=120
NotifyAccess=main

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    sudo systemctl daemon-reload
    sudo systemctl enable optic-shield
    
    echo -e "${GREEN}✓ Service installed${NC}"
    echo "  Start:  sudo systemctl start optic-shield"
    echo "  Stop:   sudo systemctl stop optic-shield"
    echo "  Status: sudo systemctl status optic-shield"
    echo "  Logs:   journalctl -u optic-shield -f"
}

# ============================================================================
# Full Installation
# ============================================================================

run_full_install() {
    local install_dir="$1"
    
    echo "=============================================="
    echo "OPTIC-SHIELD Full Installation"
    echo "=============================================="
    
    # Print platform info
    print_platform_info
    echo ""
    
    # Install dependencies
    install_system_deps || return 1
    
    # Setup venv
    setup_python_venv "$install_dir" || return 1
    
    # Install Python packages
    install_python_packages "$install_dir" || return 1
    
    # Setup directories
    setup_directories "$install_dir" || return 1
    
    # Add user to groups
    add_user_to_groups
    
    echo ""
    echo "=============================================="
    echo -e "${GREEN}Installation complete!${NC}"
    echo "=============================================="
}
