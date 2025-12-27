#!/bin/bash
# OPTIC-SHIELD Platform Detection Library
# Provides functions to detect OS type, architecture, and user groups

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# OS Detection
# ============================================================================

detect_os() {
    # Returns: os_type (raspberry_pi, linux, macos, windows)
    local os_type="unknown"
    
    case "$(uname -s)" in
        Darwin)
            os_type="macos"
            ;;
        Linux)
            if is_raspberry_pi; then
                os_type="raspberry_pi"
            else
                os_type="linux"
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)
            os_type="windows"
            ;;
    esac
    
    echo "$os_type"
}

detect_os_name() {
    # Returns: human-readable OS name
    local os_type
    os_type=$(detect_os)
    
    case "$os_type" in
        macos)
            echo "macOS $(sw_vers -productVersion 2>/dev/null || echo '')"
            ;;
        raspberry_pi)
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                echo "${PRETTY_NAME:-Raspberry Pi OS}"
            else
                echo "Raspberry Pi OS"
            fi
            ;;
        linux)
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                echo "${PRETTY_NAME:-Linux}"
            else
                echo "Linux"
            fi
            ;;
        windows)
            echo "Windows"
            ;;
        *)
            echo "Unknown OS"
            ;;
    esac
}

is_raspberry_pi() {
    # Check multiple indicators for Raspberry Pi
    
    # Check /proc/cpuinfo
    if [ -f /proc/cpuinfo ]; then
        if grep -qi "raspberry pi\|bcm" /proc/cpuinfo 2>/dev/null; then
            return 0
        fi
    fi
    
    # Check device-tree model
    if [ -f /proc/device-tree/model ]; then
        if grep -qi "raspberry pi" /proc/device-tree/model 2>/dev/null; then
            return 0
        fi
    fi
    
    # Check for vcgencmd
    if command -v vcgencmd &>/dev/null; then
        return 0
    fi
    
    # Check for Raspberry Pi specific paths
    if [ -f /opt/vc/bin/vcgencmd ]; then
        return 0
    fi
    
    return 1
}

# ============================================================================
# Architecture Detection
# ============================================================================

detect_arch() {
    # Returns: arm64, arm32, x86_64, x86
    local machine
    machine=$(uname -m)
    
    case "$machine" in
        aarch64|arm64)
            echo "arm64"
            ;;
        armv7l|armhf|arm*)
            echo "arm32"
            ;;
        x86_64|amd64)
            echo "x86_64"
            ;;
        i386|i686)
            echo "x86"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

can_run_ncnn() {
    local arch
    arch=$(detect_arch)
    
    if [ "$arch" = "arm64" ] || [ "$arch" = "x86_64" ]; then
        return 0
    fi
    return 1
}

# ============================================================================
# User and Group Detection
# ============================================================================

detect_current_user() {
    # Returns: current username
    if [ -n "$SUDO_USER" ]; then
        echo "$SUDO_USER"
    else
        echo "$(whoami)"
    fi
}

detect_user_groups() {
    # Returns: comma-separated list of groups
    local user
    user=$(detect_current_user)
    groups "$user" 2>/dev/null | cut -d: -f2 | tr ' ' ',' | sed 's/^,//'
}

user_in_group() {
    # Check if user is in a specific group
    local group_name="$1"
    local user
    user=$(detect_current_user)
    
    if groups "$user" 2>/dev/null | grep -qw "$group_name"; then
        return 0
    fi
    return 1
}

get_required_groups() {
    # Returns: space-separated list of required groups
    local os_type
    os_type=$(detect_os)
    
    case "$os_type" in
        raspberry_pi)
            echo "video gpio i2c"
            ;;
        linux)
            echo "video"
            ;;
        *)
            echo ""
            ;;
    esac
}

get_missing_groups() {
    # Returns: space-separated list of missing groups
    local required missing=""
    required=$(get_required_groups)
    
    for group in $required; do
        if ! user_in_group "$group"; then
            missing="$missing $group"
        fi
    done
    
    echo "$missing" | xargs
}

add_user_to_groups() {
    # Add current user to required groups
    local missing user
    missing=$(get_missing_groups)
    user=$(detect_current_user)
    
    if [ -z "$missing" ]; then
        echo -e "${GREEN}✓ User already in all required groups${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}Adding user '$user' to groups: $missing${NC}"
    
    for group in $missing; do
        if getent group "$group" &>/dev/null; then
            sudo usermod -aG "$group" "$user"
            echo -e "  ${GREEN}✓ Added to '$group'${NC}"
        else
            echo -e "  ${YELLOW}⚠ Group '$group' does not exist${NC}"
        fi
    done
    
    echo -e "${YELLOW}⚠ You may need to log out and back in for group changes to take effect${NC}"
}

# ============================================================================
# Hardware Detection
# ============================================================================

has_pi_camera() {
    if ! is_raspberry_pi; then
        return 1
    fi
    
    # Check libcamera
    if command -v libcamera-hello &>/dev/null; then
        if libcamera-hello --list-cameras 2>&1 | grep -q "Available cameras"; then
            return 0
        fi
    fi
    
    # Check legacy camera
    if command -v vcgencmd &>/dev/null; then
        if vcgencmd get_camera 2>/dev/null | grep -q "detected=1"; then
            return 0
        fi
    fi
    
    return 1
}

has_usb_camera() {
    # Check for video devices
    if ls /dev/video* &>/dev/null; then
        return 0
    fi
    return 1
}

has_any_camera() {
    if has_pi_camera || has_usb_camera; then
        return 0
    fi
    return 1
}

has_gpio() {
    if [ -d /sys/class/gpio ] || ls /dev/gpiochip* &>/dev/null 2>&1; then
        return 0
    fi
    return 1
}

has_i2c() {
    if ls /dev/i2c-* &>/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# ============================================================================
# Path Detection
# ============================================================================

get_install_dir() {
    # Get the installation directory
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    echo "$script_dir"
}

get_home_dir() {
    local user
    user=$(detect_current_user)
    eval echo "~$user"
}

# ============================================================================
# Python Detection
# ============================================================================

detect_python() {
    # Returns: path to Python 3.10+
    local python_cmd=""
    
    for cmd in python3.12 python3.11 python3.10 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            local version
            version=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
            local major minor
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)
            
            if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
                python_cmd=$(command -v "$cmd")
                break
            fi
        fi
    done
    
    echo "$python_cmd"
}

check_python_version() {
    local python_cmd
    python_cmd=$(detect_python)
    
    if [ -z "$python_cmd" ]; then
        echo -e "${RED}✗ Python 3.10+ not found${NC}"
        return 1
    fi
    
    local version
    version=$("$python_cmd" --version 2>&1)
    echo -e "${GREEN}✓ $version ($python_cmd)${NC}"
    return 0
}

# ============================================================================
# Print Functions
# ============================================================================

print_platform_info() {
    echo "=============================================="
    echo "OPTIC-SHIELD Platform Detection"
    echo "=============================================="
    echo -e "OS Type:      ${BLUE}$(detect_os)${NC}"
    echo -e "OS Name:      ${BLUE}$(detect_os_name)${NC}"
    echo -e "Architecture: ${BLUE}$(detect_arch)${NC}"
    echo -e "User:         ${BLUE}$(detect_current_user)${NC}"
    echo -e "Groups:       ${BLUE}$(detect_user_groups)${NC}"
    echo "----------------------------------------------"
    
    local missing
    missing=$(get_missing_groups)
    if [ -n "$missing" ]; then
        echo -e "${YELLOW}⚠ Missing groups: $missing${NC}"
    else
        echo -e "${GREEN}✓ All required groups present${NC}"
    fi
    
    echo "----------------------------------------------"
    echo -n "Camera:       "
    if has_any_camera; then
        if has_pi_camera; then
            echo -e "${GREEN}✓ Pi Camera detected${NC}"
        else
            echo -e "${GREEN}✓ USB Camera detected${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ No camera detected${NC}"
    fi
    
    echo -n "GPIO:         "
    if has_gpio; then
        echo -e "${GREEN}✓ Available${NC}"
    else
        echo -e "${YELLOW}⚠ Not available${NC}"
    fi
    
    echo -n "NCNN Support: "
    if can_run_ncnn; then
        echo -e "${GREEN}✓ Yes${NC}"
    else
        echo -e "${YELLOW}⚠ No ($(detect_arch))${NC}"
    fi
    
    echo "=============================================="
}

# Run if executed directly
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    print_platform_info
fi
