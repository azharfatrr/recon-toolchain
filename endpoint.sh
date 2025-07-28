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

SCRIPTS_PATH="$PPATH/scripts"

RESULT_PATH="$PPATH/results/$TARGET"
RAW_PATH="$RESULT_PATH/raw/endpoints"
ACTIVE_DOMAINS="$RESULT_PATH/subdomains_active.txt"

URLFINDER_RAW="$RAW_PATH/urlfinder.txt"
GAU_RAW="$RAW_PATH/gau.txt"
WAYBACKURLS_RAW="$RAW_PATH/waybackurls.txt"
KATANA_RAW="$RAW_PATH/katana.txt"
SITEMAP_RAW="$RAW_PATH/sitemap.txt"

COMBINED_RAW="$RAW_PATH/combined.txt"
FILTERED_URLS="$RESULT_PATH/endpoints.txt"
SORTED_BY_EXT="$RESULT_PATH/endpoints_extension.txt"
ACTIVE_URLS="$RESULT_PATH/endpoints_active.txt"
PAGE_HTML="$RESULT_PATH/html"
CREDENTIALS="$RESULT_PATH/credentials.txt"

# --------------------------------------
# Force cleanup
if [[ "$FORCE" == "--force" ]]; then
    rm -rf "$RAW_PATH"
    rm -f "$FILTERED_URLS" "$SORTED_BY_EXT" "$ACTIVE_URLS" "$PAGE_HTML" "$CREDENTIALS"
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

# # --------------------------------------
# # Run Gau
# if [[ ! -s "$GAU_RAW" ]]; then
#     echo "[INFO] Running Gau for..."
#     cat "$ACTIVE_DOMAINS" | gau --o "$GAU_RAW" 1>/dev/null
# else
#     echo "[INFO] Skipping Gau – results already exist."
# fi

# # --------------------------------------
# # Run Waybackurls
# if [[ ! -s "$WAYBACKURLS_RAW" ]]; then
#     echo "[INFO] Running Waybackurls for..."
#     cat "$ACTIVE_DOMAINS" | waybackurls > "$WAYBACKURLS_RAW" 1>/dev/null
# else
#     echo "[INFO] Skipping Waybackurls – results already exist."
# fi

# --------------------------------------
# Run Katana
if [[ ! -s "$KATANA_RAW" ]]; then
    echo "[INFO] Running Katana on active subdomains..."
    katana -silent -list "$ACTIVE_DOMAINS" -jc -xhr -kf all -d 3 -fs rdn -o "$KATANA_RAW" 1>/dev/null
else
    echo "[INFO] Skipping Katana – results already exist."
fi

# --------------------------------------
# Merge and deduplicate raw URLs
echo "[INFO] Merging and deduplicating raw URLs..."
cat "$URLFINDER_RAW" "$KATANA_RAW" | sort -u > "$COMBINED_RAW"

# --------------------------------------
# Run Parse_Sitemap.py
if [[ ! -s "$SITEMAP_RAW" ]]; then
    echo "[INFO] Parsing sitemap..."
    touch "$SITEMAP_RAW"
    python3 "$SCRIPTS_PATH/parse_sitemap.py" -i "$COMBINED_RAW" -o "$SITEMAP_RAW" 1>/dev/null
else
    echo "[INFO] Skipping sitemap parsing – already done."
fi


# --------------------------------------
# Recombine raw URLs with parsed sitemap
echo "[INFO] Recombining raw URLs with parsed sitemap..."
cat "$COMBINED_RAW" "$SITEMAP_RAW" | sort -u > "$COMBINED_RAW.tmp"
mv "$COMBINED_RAW.tmp" "$COMBINED_RAW"

# --------------------------------------
# Filter with urless
echo "[INFO] Filtering endpoints using urless..."
uro < "$COMBINED_RAW" | urless > "$FILTERED_URLS"

# --------------------------------------
# Sort filtered endpoints by file extension
echo "[INFO] Sorting by file extension..."

awk '{
    url=$0;
    split(url, parts, "?");                     # Remove query string
    split(parts[1], pathParts, "/");
    last=pathParts[length(pathParts)];
    split(last, extParts, ".");
    ext=(length(extParts) > 1 ? extParts[length(extParts)] : "noext");
    print ext "\t" url;
}' "$FILTERED_URLS" | sort -k1,1 | cut -f2- > "$SORTED_BY_EXT"

# -----------------------------------------
# Get active endpoints
echo "[INFO] Getting active endpoints..."
if [[ -s "$ACTIVE_URLS" ]]; then
    echo "[INFO] Skipping scanning active endpoints - already exists and is not empty."
else
    : > "$ACTIVE_URLS"
    python3 "$SCRIPTS_PATH/parse_endpoint.py" -i "$FILTERED_URLS" -o "$ACTIVE_URLS" --html-dump-dir "$PAGE_HTML"
fi

# -----------------------------------------
# Get credentials
echo "[INFO] Getting credentials from active endpoints..."
if [[ -s "$CREDENTIALS" ]]; then
    echo "[INFO] Skipping scanning credentials - already exists and is not empty."
else
    : > "$CREDENTIALS"
    python3 "$SCRIPTS_PATH/parse_credential.py" -i "$PAGE_HTML" -o "$CREDENTIALS"
fi

# --------------------------------------
# Completion
echo "[DONE] Filtered endpoints saved in: $FILTERED_URLS"
