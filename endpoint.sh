#!/bin/bash
# Endpoint enumeration script using urlfinder, gau, and urless

echo "[INFO] Enumerating endpoints for $1"

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

RESULT_PATH="$PPATH/results/$TARGET"
RAW_PATH="$RESULT_PATH/raw/endpoints"
ACTIVE_DOMAINS="$RESULT_PATH/subdomains_active.txt"

URLFINDER_RAW="$RAW_PATH/urlfinder.txt"
GAU_RAW="$RAW_PATH/gau.txt"
WAYBACKURLS_RAW="$RAW_PATH/waybackurls.txt"

COMBINED_RAW="$RAW_PATH/all_endpoints_combined.txt"
FILTERED_URLS="$RESULT_PATH/endpoints.txt"

# --------------------------------------
# Force cleanup
if [[ "$FORCE" == "--force" ]]; then
    rm -rf "$RAW_PATH"
    rm -f "$URLFINDER_RAW" "$GAU_RAW" "$WAYBACKURLS_RAW" "$COMBINED_RAW" "$FILTERED_URLS"
fi

# --------------------------------------
# Setup folders
mkdir -p "$RESULT_PATH" "$RAW_PATH"

# --------------------------------------
# Validate domain list
if [[ ! -s "$ACTIVE_DOMAINS" ]]; then
    echo "[ERROR] Active subdomain list not found or empty: $ACTIVE_DOMAINS"
    exit 1
fi

# --------------------------------------
# Run Urlfinder
if [[ ! -s "$URLFINDER_RAW" ]]; then
    echo "[INFO] Running Urlfinder..."
    urlfinder -silent -list "$ACTIVE_DOMAINS" -o "$URLFINDER_RAW" 1>/dev/null
else
    echo "[INFO] Skipping Urlfinder – results already exist."
fi


# --------------------------------------
# Run Gau
if [[ ! -s "$GAU_RAW" ]]; then
    echo "[INFO] Running Gau for..."
    cat "$ACTIVE_DOMAINS" | gau --o "$GAU_RAW" 1>/dev/null
else
    echo "[INFO] Skipping Gau – results already exist."
fi

# --------------------------------------
# Run Waybackurls
if [[ ! -s "$WAYBACKURLS_RAW" ]]; then
    echo "[INFO] Running Waybackurls for..."
    cat "$ACTIVE_DOMAINS" | waybackurls > "$WAYBACKURLS_RAW" 1>/dev/null
else
    echo "[INFO] Skipping Waybackurls – results already exist."
fi

# --------------------------------------
# Merge and deduplicate raw URLs
echo "[INFO] Merging and deduplicating raw URLs..."
cat "$URLFINDER_RAW" "$GAU_RAW" "$WAYBACKURLS_RAW" | sort -u > "$COMBINED_RAW"

# --------------------------------------
# Filter with urless
echo "[INFO] Filtering endpoints using urless..."
urless -i "$COMBINED_RAW" -o "$FILTERED_URLS" 1>/dev/null

# --------------------------------------
# Completion
echo "[DONE] Filtered endpoints saved in: $FILTERED_URLS"
