#!/bin/bash

# Default config
INPUT=""
OUTPUT=""
DELAY=1
TIMEOUT=10
RETRIES=3
VERBOSE=0
KEYWORDS=("404" "not found" "tidak ditemukan")

print_usage() {
  echo "Usage: $0 -i <input_file> [-o <output_file>] [--delay N] [--timeout N] [--retries N] [--keywords kw1,kw2] [-v]"
  exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -i|--input) INPUT="$2"; shift 2 ;;
    -o|--output) OUTPUT="$2"; shift 2 ;;
    --delay) DELAY="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --retries) RETRIES="$2"; shift 2 ;;
    --keywords) IFS=',' read -r -a KEYWORDS <<< "$2"; shift 2 ;;
    -v|--verbose) VERBOSE=1; shift ;;
    *) print_usage ;;
  esac
done

if [[ ! -f "$INPUT" ]]; then
  echo "[!] Input file not found: $INPUT"
  print_usage
fi

[[ -n "$OUTPUT" ]] && > "$OUTPUT"  # Clear output file if exists

log() {
  [[ "$VERBOSE" -eq 1 ]] && echo "$@"
}

total=$(wc -l < "$INPUT")
log "Processing $total URLs from: $INPUT"
[[ -n "$OUTPUT" ]] && log "Valid URLs will be saved to: $OUTPUT"

# httpx options
httpx_opts=(-silent -status-code -title -timeout "$TIMEOUT")

# Main loop
index=0
while IFS= read -r url; do
  ((index++))
  log "[$index/$total] Checking: $url"

  for ((attempt=1; attempt<=RETRIES; attempt++)); do
    result=$(echo "$url" | httpx "${httpx_opts[@]}")
    [[ -z "$result" ]] && log "  [!] No response (attempt $attempt)" && sleep "$DELAY" && continue

    status=$(echo "$result" | awk '{print $2}')
    title=$(echo "$result" | cut -d ' ' -f3-)
    title_lc=$(echo "$title" | tr '[:upper:]' '[:lower:]')

    if [[ "$status" == "404" ]]; then
      log "  [404] $url (real 404)"
      break
    fi

    is_not_found=0
    for kw in "${KEYWORDS[@]}"; do
      if [[ "$title_lc" == *"$kw"* ]]; then
        log "  [fake404] $url (title contains '$kw')"
        is_not_found=1
        break
      fi
    done

    if [[ "$is_not_found" -eq 0 ]]; then
      log "  [ok] $url"
      [[ -n "$OUTPUT" ]] && echo "$url" >> "$OUTPUT"
    fi

    break  # Exit retry loop on success
  done

  sleep "$DELAY"
done < "$INPUT"
