#!/bin/bash
# ============================================================================
# OPTIC-SHIELD Auto Setup Script
# ============================================================================
# 
# Comprehensive setup script for OPTIC-SHIELD Wildlife Detection System.
# Automatically detects platform, installs dependencies, and validates setup.
#
# Usage:
#   ./auto_setup.sh              # Full installation
#   ./auto_setup.sh --validate   # Only run validation
#   ./auto_setup.sh --info       # Only show platform info
#   ./auto_setup.sh --help       # Show help
#
# ============================================================================

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source libraries
source "$SCRIPT_DIR/lib/platform_detect.sh"
source "$SCRIPT_DIR/lib/install_deps.sh"
source "$SCRIPT_DIR/lib/validate.sh"

# ============================================================================
# Banner
# ============================================================================

print_banner() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}                                                               ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}   🦁 ${GREEN}OPTIC-SHIELD${NC} Wildlife Detection System                  ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}      Auto Setup & Installation                               ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}                                                               ${BLUE}║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ============================================================================
# Help
# ============================================================================

show_help() {
    print_banner
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h        Show this help message"
    echo "  --info, -i        Show platform information only"
    echo "  --validate, -v    Run validation checks only"
    echo "  --install         Run full installation (default)"
    echo "  --service         Install systemd service (Linux only)"
    echo "  --test            Run tests after installation"
    echo "  --all             Full installation + service + tests"
    echo ""
    echo "Examples:"
    echo "  $0                  # Run full installation"
    echo "  $0 --validate       # Check if everything is properly set up"
    echo "  $0 --all            # Full setup with service and tests"
    echo ""
}

# ============================================================================
# Export Model (if possible)
# ============================================================================

export_model() {
    local python_cmd="$INSTALL_DIR/venv/bin/python"
    local export_script="$SCRIPT_DIR/export_model.py"
    
    echo -e "\n${BLUE}Checking YOLO model...${NC}"
    
    # Check if NCNN model already exists
    if [ -d "$INSTALL_DIR/models/yolo11n_ncnn_model" ]; then
        echo -e "${GREEN}✓ NCNN model already exists${NC}"
        return 0
    fi
    
    # Check if we can export
    if ! can_run_ncnn; then
        echo -e "${YELLOW}⚠ NCNN not supported on this architecture${NC}"
        echo "  Model will be downloaded on first run"
        return 0
    fi
    
    # Try to export
    if [ -f "$export_script" ]; then
        echo "Exporting YOLO model to NCNN format..."
        if "$python_cmd" "$export_script" 2>/dev/null; then
            echo -e "${GREEN}✓ Model exported successfully${NC}"
        else
            echo -e "${YELLOW}⚠ Model export failed, will download on first run${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ Export script not found, model will be downloaded on first run${NC}"
    fi
}

# ============================================================================
# Run Tests
# ============================================================================

run_tests() {
    local python_cmd="$INSTALL_DIR/venv/bin/python"
    local test_script="$SCRIPT_DIR/run_tests.py"
    
    echo -e "\n${BLUE}Running tests...${NC}"
    
    if [ -f "$test_script" ]; then
        if "$python_cmd" "$test_script"; then
            return 0
        else
            return 1
        fi
    else
        echo -e "${YELLOW}⚠ Test script not found${NC}"
        return 0
    fi
}

# ============================================================================
# Final Summary
# ============================================================================

print_summary() {
    local status="$1"
    
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}                     SETUP COMPLETE                            ${BLUE}║${NC}"
    echo -e "${BLUE}╠═══════════════════════════════════════════════════════════════╣${NC}"
    
    local os_name
    os_name=$(detect_os_name)
    echo -e "${BLUE}║${NC}  Platform: $os_name"
    echo -e "${BLUE}║${NC}  User:     $(detect_current_user)"
    echo -e "${BLUE}║${NC}  Install:  $INSTALL_DIR"
    
    echo -e "${BLUE}╠═══════════════════════════════════════════════════════════════╣${NC}"
    
    if [ "$status" = "success" ]; then
        echo -e "${BLUE}║${NC}                                                               ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}   ${GREEN}✅ TESTED OK - Ready to use!${NC}                              ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}                                                               ${BLUE}║${NC}"
    else
        echo -e "${BLUE}║${NC}                                                               ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}   ${YELLOW}⚠ Setup complete with warnings${NC}                           ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}                                                               ${BLUE}║${NC}"
    fi
    
    echo -e "${BLUE}╠═══════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${BLUE}║${NC}  Next Steps:                                                 ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}                                                               ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  1. Activate venv:                                           ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}     source venv/bin/activate                                 ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}                                                               ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  2. Run the service:                                         ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}     python main.py                                           ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}                                                               ${BLUE}║${NC}"
    
    local os_type
    os_type=$(detect_os)
    if [ "$os_type" = "raspberry_pi" ] || [ "$os_type" = "linux" ]; then
        echo -e "${BLUE}║${NC}  3. Or start as service:                                     ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}     sudo systemctl start optic-shield                        ${BLUE}║${NC}"
        echo -e "${BLUE}║${NC}                                                               ${BLUE}║${NC}"
    fi
    
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ============================================================================
# Main Installation
# ============================================================================

do_install() {
    print_banner
    
    # Print platform info
    print_platform_info
    
    # Confirm installation
    echo ""
    echo -e "${YELLOW}This will install OPTIC-SHIELD in: $INSTALL_DIR${NC}"
    echo ""
    read -p "Continue with installation? [Y/n] " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]?$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    
    # Run full install
    run_full_install "$INSTALL_DIR"
    
    # Export model if possible
    export_model
}

do_validate() {
    print_banner
    run_validation "$INSTALL_DIR"
}

do_service() {
    install_systemd_service "$INSTALL_DIR"
}

do_all() {
    do_install
    do_service
    
    echo ""
    echo "Running validation..."
    if run_validation "$INSTALL_DIR"; then
        print_summary "success"
    else
        print_summary "warning"
    fi
}

# ============================================================================
# Parse Arguments
# ============================================================================

main() {
    local action="install"
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                show_help
                exit 0
                ;;
            --info|-i)
                action="info"
                shift
                ;;
            --validate|-v)
                action="validate"
                shift
                ;;
            --install)
                action="install"
                shift
                ;;
            --service)
                action="service"
                shift
                ;;
            --test)
                action="test"
                shift
                ;;
            --all)
                action="all"
                shift
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
    
    case "$action" in
        info)
            print_banner
            print_platform_info
            ;;
        validate)
            do_validate
            ;;
        install)
            do_install
            echo ""
            echo "Running validation..."
            if run_validation "$INSTALL_DIR"; then
                print_summary "success"
            else
                print_summary "warning"
            fi
            ;;
        service)
            do_service
            ;;
        test)
            run_tests
            ;;
        all)
            do_all
            ;;
    esac
}

# Run main
main "$@"
