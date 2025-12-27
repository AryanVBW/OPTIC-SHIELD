#!/bin/bash
# OPTIC-SHIELD Validation Library
# Functions to validate the installation

# Source platform detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/platform_detect.sh"

# Validation results
declare -A VALIDATION_RESULTS
VALIDATION_PASS=0
VALIDATION_FAIL=0
VALIDATION_WARN=0

# ============================================================================
# Validation Helpers
# ============================================================================

check_pass() {
    local name="$1"
    local message="$2"
    VALIDATION_RESULTS["$name"]="PASS"
    ((VALIDATION_PASS++))
    echo -e "  ${GREEN}✓${NC} $name: $message"
}

check_fail() {
    local name="$1"
    local message="$2"
    VALIDATION_RESULTS["$name"]="FAIL"
    ((VALIDATION_FAIL++))
    echo -e "  ${RED}✗${NC} $name: $message"
}

check_warn() {
    local name="$1"
    local message="$2"
    VALIDATION_RESULTS["$name"]="WARN"
    ((VALIDATION_WARN++))
    echo -e "  ${YELLOW}⚠${NC} $name: $message"
}

check_skip() {
    local name="$1"
    local message="$2"
    VALIDATION_RESULTS["$name"]="SKIP"
    echo -e "  ${BLUE}○${NC} $name: $message (skipped)"
}

# ============================================================================
# Basic Checks
# ============================================================================

validate_python() {
    local python_cmd
    python_cmd=$(detect_python)
    
    if [ -z "$python_cmd" ]; then
        check_fail "Python" "Python 3.10+ not found"
        return 1
    fi
    
    local version
    version=$("$python_cmd" --version 2>&1)
    check_pass "Python" "$version"
    return 0
}

validate_venv() {
    local install_dir="$1"
    local venv_dir="$install_dir/venv"
    
    if [ ! -d "$venv_dir" ]; then
        check_fail "VirtualEnv" "Not found at $venv_dir"
        return 1
    fi
    
    if [ ! -f "$venv_dir/bin/activate" ]; then
        check_fail "VirtualEnv" "Invalid venv (missing activate)"
        return 1
    fi
    
    check_pass "VirtualEnv" "Found at $venv_dir"
    return 0
}

validate_core_deps() {
    local install_dir="$1"
    local venv_dir="$install_dir/venv"
    local python_cmd="$venv_dir/bin/python"
    
    if [ ! -f "$python_cmd" ]; then
        check_fail "CoreDeps" "Python not found in venv"
        return 1
    fi
    
    local missing=""
    
    # Check ultralytics
    if ! "$python_cmd" -c "import ultralytics" 2>/dev/null; then
        missing="$missing ultralytics"
    fi
    
    # Check numpy
    if ! "$python_cmd" -c "import numpy" 2>/dev/null; then
        missing="$missing numpy"
    fi
    
    # Check PIL
    if ! "$python_cmd" -c "from PIL import Image" 2>/dev/null; then
        missing="$missing Pillow"
    fi
    
    # Check PyYAML
    if ! "$python_cmd" -c "import yaml" 2>/dev/null; then
        missing="$missing PyYAML"
    fi
    
    if [ -n "$missing" ]; then
        check_fail "CoreDeps" "Missing:$missing"
        return 1
    fi
    
    check_pass "CoreDeps" "All core dependencies installed"
    return 0
}

validate_opencv() {
    local install_dir="$1"
    local python_cmd="$install_dir/venv/bin/python"
    
    if [ ! -f "$python_cmd" ]; then
        check_fail "OpenCV" "Python not found in venv"
        return 1
    fi
    
    if "$python_cmd" -c "import cv2" 2>/dev/null; then
        local version
        version=$("$python_cmd" -c "import cv2; print(cv2.__version__)" 2>/dev/null)
        check_pass "OpenCV" "Version $version"
        return 0
    else
        check_fail "OpenCV" "Not installed"
        return 1
    fi
}

# ============================================================================
# Directory Checks
# ============================================================================

validate_directories() {
    local install_dir="$1"
    local all_ok=true
    
    for dir in "data" "data/images" "logs" "models" "config"; do
        local full_path="$install_dir/$dir"
        if [ -d "$full_path" ]; then
            if [ -w "$full_path" ]; then
                check_pass "Dir:$dir" "Exists and writable"
            else
                check_warn "Dir:$dir" "Exists but not writable"
                all_ok=false
            fi
        else
            check_fail "Dir:$dir" "Does not exist"
            all_ok=false
        fi
    done
    
    $all_ok
}

validate_config() {
    local install_dir="$1"
    local config_file="$install_dir/config/config.yaml"
    
    if [ -f "$config_file" ]; then
        check_pass "Config" "config.yaml found"
        return 0
    else
        check_fail "Config" "config.yaml not found"
        return 1
    fi
}

validate_model() {
    local install_dir="$1"
    local models_dir="$install_dir/models"
    
    # Check for NCNN model
    if [ -d "$models_dir/yolo11n_ncnn_model" ]; then
        check_pass "Model" "NCNN model found"
        return 0
    fi
    
    # Check for PT model
    if [ -f "$models_dir/yolo11n.pt" ]; then
        check_pass "Model" "PyTorch model found (will download NCNN on first run)"
        return 0
    fi
    
    # Check if ultralytics will auto-download
    check_warn "Model" "No model found (will be downloaded on first run)"
    return 0
}

# ============================================================================
# Hardware Checks
# ============================================================================

validate_camera() {
    local os_type
    os_type=$(detect_os)
    
    if has_pi_camera; then
        check_pass "Camera" "Pi Camera detected"
        return 0
    elif has_usb_camera; then
        check_pass "Camera" "USB Camera detected"
        return 0
    else
        if [ "$os_type" = "raspberry_pi" ]; then
            check_fail "Camera" "No camera detected"
            return 1
        else
            check_skip "Camera" "Not on Raspberry Pi"
            return 0
        fi
    fi
}

validate_gpio() {
    local os_type
    os_type=$(detect_os)
    
    if [ "$os_type" != "raspberry_pi" ]; then
        check_skip "GPIO" "Not on Raspberry Pi"
        return 0
    fi
    
    if has_gpio; then
        check_pass "GPIO" "Available"
        return 0
    else
        check_warn "GPIO" "Not available"
        return 0
    fi
}

# ============================================================================
# Permission Checks
# ============================================================================

validate_permissions() {
    local missing
    missing=$(get_missing_groups)
    
    if [ -z "$missing" ]; then
        check_pass "Groups" "User in all required groups"
        return 0
    else
        check_warn "Groups" "Missing groups: $missing"
        return 0
    fi
}

# ============================================================================
# Service Checks
# ============================================================================

validate_service() {
    local os_type
    os_type=$(detect_os)
    
    if [ "$os_type" != "raspberry_pi" ] && [ "$os_type" != "linux" ]; then
        check_skip "Service" "Systemd not available on $os_type"
        return 0
    fi
    
    if ! command -v systemctl &>/dev/null; then
        check_skip "Service" "systemctl not found"
        return 0
    fi
    
    if systemctl list-unit-files | grep -q "optic-shield.service"; then
        local status
        status=$(systemctl is-enabled optic-shield 2>/dev/null || echo "disabled")
        check_pass "Service" "Installed ($status)"
        return 0
    else
        check_warn "Service" "Not installed"
        return 0
    fi
}

# ============================================================================
# Full Validation
# ============================================================================

run_validation() {
    local install_dir="$1"
    
    echo ""
    echo "=============================================="
    echo "OPTIC-SHIELD Setup Validation"
    echo "=============================================="
    echo ""
    echo "Checking installation at: $install_dir"
    echo ""
    
    # Reset counters
    VALIDATION_PASS=0
    VALIDATION_FAIL=0
    VALIDATION_WARN=0
    
    echo "--- Basic Checks ---"
    validate_python
    validate_venv "$install_dir"
    validate_core_deps "$install_dir"
    validate_opencv "$install_dir"
    
    echo ""
    echo "--- Directory Checks ---"
    validate_directories "$install_dir"
    validate_config "$install_dir"
    validate_model "$install_dir"
    
    echo ""
    echo "--- Hardware Checks ---"
    validate_camera
    validate_gpio
    
    echo ""
    echo "--- Permission Checks ---"
    validate_permissions
    validate_service
    
    # Print summary
    echo ""
    echo "=============================================="
    echo "Validation Summary"
    echo "=============================================="
    echo -e "  ${GREEN}Passed:${NC}  $VALIDATION_PASS"
    echo -e "  ${RED}Failed:${NC}  $VALIDATION_FAIL"
    echo -e "  ${YELLOW}Warnings:${NC} $VALIDATION_WARN"
    echo ""
    
    if [ $VALIDATION_FAIL -eq 0 ]; then
        echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║       ✅ VALIDATION PASSED               ║${NC}"
        echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
        return 0
    else
        echo -e "${RED}╔══════════════════════════════════════════╗${NC}"
        echo -e "${RED}║       ❌ VALIDATION FAILED               ║${NC}"
        echo -e "${RED}║  Please fix the issues above             ║${NC}"
        echo -e "${RED}╚══════════════════════════════════════════╝${NC}"
        return 1
    fi
}

# Run if executed directly
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    install_dir=$(get_install_dir)
    run_validation "$install_dir"
fi
