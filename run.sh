#!/bin/bash
# Unified scan runner for subdomain + port scan with single log file (UTC timestamps)

# --------------------------------------
# Check input
if [ -z "$1" ]; then
    echo "[ERROR] No target provided. Usage: $0 <target> [--force]"
    exit 1
fi

# --------------------------------------
# Configuration
TARGET="$1"
FORCE="$2"
PPATH=$(pwd)
LOG_DIR="$PPATH/logs/$TARGET"
mkdir -p "$LOG_DIR"

# Get UTC timestamp for filename
UTC_TIMESTAMP=$(date -u +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/run_${UTC_TIMESTAMP}.log"

SUBDOMAIN_SCRIPT="./subdomain.sh"
PORT_SCAN_SCRIPT="./port_scanning.sh"
ENDPOINT_SCRIPT="./endpoint.sh"
VULNERABILITY_SCRIPT="./vulnerability-assessment.sh"

# --------------------------------------
# Run all scripts with combined logging
{
    echo "========== Scan started: $(date -u +"%Y-%m-%d %H:%M:%S UTC") =========="
    echo

    echo "[*] $(date -u +"%Y-%m-%d %H:%M:%S UTC") - Running subdomain enumeration..."
    bash "$SUBDOMAIN_SCRIPT" "$TARGET" "$FORCE"

    echo
    echo "[*] $(date -u +"%Y-%m-%d %H:%M:%S UTC") - Running port scanning..."
    bash "$PORT_SCAN_SCRIPT" "$TARGET" "$FORCE"

    echo
    echo "[*] $(date -u +"%Y-%m-%d %H:%M:%S UTC") - Endpoint scanning..."
    bash "$ENDPOINT_SCRIPT" "$TARGET" "$FORCE"

    echo
    echo "[*] $(date -u +"%Y-%m-%d %H:%M:%S UTC") - Vulnerability Assessment..."
    bash "$VULNERABILITY_SCRIPT" "$TARGET" "$FORCE"

    echo
    echo "========== Scan completed: $(date -u +"%Y-%m-%d %H:%M:%S UTC") =========="
} | tee "$LOG_FILE"

# --------------------------------------
# Completion
echo "[DONE] All results and logs stored under: $LOG_DIR"
