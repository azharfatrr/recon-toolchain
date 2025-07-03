#!/bin/bash
# Subdomain enumeration script using subfinder and amass

echo "[INFO] Scanning subdomain $1"

if [ -z "$1" ]; then
    echo "[ERROR] No target provided. Usage: $0 <target> [--force]"
    exit 1
fi

# --------------------------------------
# Configuration
TARGET=$1
FORCE=$2
PPATH=$(pwd)
TOOLS_PATH=$HOME/Tools
RESOLVER="$TOOLS_PATH/resolvers_trusted.txt"

RESULT_PATH="$PPATH/results/$TARGET"
RAW_PATH="$RESULT_PATH/raw/subdomains"

# Output file paths
SUBFINDER_RAW="$RAW_PATH/subfinder.txt"
AMASS_RAW="$RAW_PATH/amass.txt"
AMASS_PARSED="$RAW_PATH/amass_subdomains.txt"
DNSX_RAW="$RAW_PATH/dnsx.txt"

SUBDOMAINS="$RESULT_PATH/subdomains.txt"
SUBDOMAIN_IPS="$RESULT_PATH/subdomains_ip.txt"
ACTIVE_SUBDOMAINS="$RESULT_PATH/subdomains_active.txt"
ACTIVE_IPS="$RESULT_PATH/subdomains_active_ip.txt"

# --------------------------------------
# Force cleanup
if [[ "$FORCE" == "--force" ]]; then
    rm -rf "$RAW_PATH"
    rm -f "$SUBDOMAINS" "$SUBDOMAIN_IPS" "$ACTIVE_SUBDOMAINS" "$ACTIVE_IPS"
fi

# --------------------------------------
# Setup
mkdir -p "$RESULT_PATH" "$RAW_PATH"

# --------------------------------------
# Run Subfinder
if [[ "$FORCE" == "--force" || ! -s "$SUBFINDER_RAW" ]]; then
    echo "[INFO] Running Subfinder for $TARGET..."
    subfinder -d "$TARGET" -o "$SUBFINDER_RAW" --silent 1>/dev/null
    echo "$TARGET" | anew "$SUBFINDER_RAW" 1>/dev/null
else
    echo "[INFO] Skipping Subfinder – results already exist."
fi

# --------------------------------------
# Run Amass
if [[ "$FORCE" == "--force" || ! -s "$AMASS_RAW" ]]; then
    echo "[INFO] Running Amass for $TARGET..."
    if [[ -f "$RESOLVER" ]]; then
        amass enum -d "$TARGET" -o "$AMASS_RAW" -silent -nocolor -rf "$RESOLVER" 1>/dev/null
    else
        amass enum -d "$TARGET" -o "$AMASS_RAW" -silent -nocolor 1>/dev/null
    fi
else
    echo "[INFO] Skipping Amass – results already exist."
fi

# --------------------------------------
# Extract subdomains from Amass output
grep -Eo "([a-zA-Z0-9-]+\.)*${TARGET//./\\.}" "$AMASS_RAW" | \
grep -E "^([a-zA-Z0-9-]+\.)*${TARGET//./\\.}$" | \
anew "$AMASS_PARSED" 1>/dev/null

# --------------------------------------
# Combine subfinder and amass results, sorted by length
awk '{ print length, $0 }' "$SUBFINDER_RAW" "$AMASS_PARSED" | \
sort -n | cut -d' ' -f2- | \
anew "$SUBDOMAINS" 1>/dev/null

# --------------------------------------
# Run Dnsx
if [[ "$FORCE" == "--force" || ! -s "$DNSX_RAW" ]]; then
    echo "[INFO] Running Dnsx for $TARGET..."
    if [[ -f "$RESOLVER" ]]; then
        dnsx -l "$SUBDOMAINS" -o "$DNSX_RAW" -a -resp -silent -no-color -r "$RESOLVER" 1>/dev/null
    else
        dnsx -l "$SUBDOMAINS" -o "$DNSX_RAW" -a -resp -silent -no-color 1>/dev/null
    fi
else
    echo "[INFO] Skipping Dnsx – results already exist."
fi

# --------------------------------------
# Extract IP addresses from dnsx output
echo "[INFO] Extracting Subdomains & IP addresses from active subdomains..."
awk '{ gsub(/[\[\]]/, "", $NF); print $NF }' "$DNSX_RAW" | sort -u | anew "$ACTIVE_IPS" 1>/dev/null

# --------------------------------------
# Extract resolved subdomain names only
awk '{ print $1 }' "$DNSX_RAW" | sort -u | anew "$ACTIVE_SUBDOMAINS" 1>/dev/null

# --------------------------------------
# Extract subdomains with IPs (include N/A for unresolved)
awk '{ 
    gsub(/[\[\]]/, "", $NF); 
    print $1, $NF 
}' "$DNSX_RAW" > "$SUBDOMAIN_IPS.tmp"

awk 'FNR==NR { ipmap[$1]=$2; next } { 
    ip = ($1 in ipmap) ? ipmap[$1] : "N/A"; 
    print $1, ip 
}' "$SUBDOMAIN_IPS.tmp" "$SUBDOMAINS" | \
awk '{ print length($1), $0 }' | sort -n | cut -d' ' -f2- | \
anew "$SUBDOMAIN_IPS" 1>/dev/null

rm -f "$SUBDOMAIN_IPS.tmp"

echo "[DONE] All results stored in: $RESULT_PATH"
