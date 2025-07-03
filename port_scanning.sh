#!/bin/bash
# Port scanning script using only Nmap

echo "[INFO] Scanning ports for $1"

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
TOOLS_PATH="$HOME/Tools"

RESULT_PATH="$PPATH/results/$TARGET"
RAW_PATH="$RESULT_PATH/raw/port_scanning"
IP_LIST="$RESULT_PATH/subdomains_active_ip.txt"

NMAP_RAW="$RAW_PATH/nmap.txt"
NMAP_PARSED="$RESULT_PATH/ports.txt"

# --------------------------------------
# Force cleanup
if [[ "$FORCE" == "--force" ]]; then
    rm -rf "$RAW_PATH"
    rm -f "$NMAP_RAW" "$NMAP_PARSED"
fi

# --------------------------------------
# Setup folders
mkdir -p "$RESULT_PATH" "$RAW_PATH"

# --------------------------------------
# Validate IP list
if [[ ! -s "$IP_LIST" ]]; then
    echo "[ERROR] IP list not found or empty: $IP_LIST"
    exit 1
fi

# --------------------------------------
# Run Nmap
if [[ -s "$NMAP_PARSED" ]]; then
    echo "[INFO] Skipping Nmap – parsed results already exist."
else
    echo "[INFO] Running Nmap scan on target IPs..."
    nmap -iL "$IP_LIST" -T4 -sS -Pn -oN "$NMAP_RAW" 1>/dev/null
fi

# --------------------------------------
# Parse Nmap output
echo "[INFO] Parsing Nmap output..."
> "$NMAP_PARSED"
awk '
    /^Nmap scan report for / {
        if (match($0, /\(([0-9.]+)\)/, m)) {
            ip = m[1]
        } else {
            ip = $NF
        }
    }
    /^[0-9]+\/tcp\s+open/ {
        port = $1
        svc = $3
        gsub("/tcp", "", port)
        printf "%s:%s %s\n", ip, port, svc
    }
' "$NMAP_RAW" > "$NMAP_PARSED"

# --------------------------------------
# Completion
echo "[DONE] All results stored in: $RESULT_PATH"
