#!/bin/bash
# Excel report generator wrapper script

echo "[INFO] Generating Excel report for $1"

# --------------------------------------
# Check input
if [ -z "$1" ]; then
    echo "[ERROR] No target provided. Usage: $0 <target>"
    exit 1
fi

# --------------------------------------
# Configuration
TARGET="$1"
PPATH=$(pwd)
SCRIPTS_PATH="$PPATH/scripts"
RESULT_PATH="$PPATH/results/$TARGET"

SUBDOMAINS_FILE="$RESULT_PATH/subdomains_ip.txt"
PORTS_FILE="$RESULT_PATH/ports.txt"
ENDPOINTS_FILE="$RESULT_PATH/endpoints.txt"
VULNS_FILE="$RESULT_PATH/vulnerability/merged_results_json.txt"

OUTPUT_FILE="$RESULT_PATH/dashboard.xlsx"

# --------------------------------------
# Validate input files
if [[ ! -f "$SUBDOMAINS_FILE" ]]; then
    echo "[ERROR] Subdomains file not found: $SUBDOMAINS_FILE"
    exit 1
fi
if [[ ! -f "$PORTS_FILE" ]]; then
    echo "[ERROR] Ports file not found: $PORTS_FILE"
    exit 1
fi
if [[ ! -f "$ENDPOINTS_FILE" ]]; then
    echo "[ERROR] Endpoints file not found: $ENDPOINTS_FILE"
    exit 1
fi
if [[ ! -f "$VULNS_FILE" ]]; then
    echo "[ERROR] Vulnerability file not found: $VULNS_FILE"
    exit 1
fi

# --------------------------------------
# Run Python generator
echo "[INFO] Running Excel generator..."
python3 "$SCRIPTS_PATH/generate_excel.py" \
    --subdomains "$SUBDOMAINS_FILE" \
    --ports "$PORTS_FILE" \
    --endpoints "$ENDPOINTS_FILE" \
    --vulns "$VULNS_FILE" \
    --output "$OUTPUT_FILE"

# --------------------------------------
# Completion
echo "[DONE] Excel report generated"
