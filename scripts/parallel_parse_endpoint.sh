#!/bin/bash

# --------- DEFAULT CONFIGURATION ----------
INPUT_FILE=""
CHUNKS=2
SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"/parse_endpoint.py
RESULT_DIR=""
OUTPUT_FILE=""
# ------------------------------------------

print_usage() {
  echo "Usage: $0 -i <input_file> -r <result_dir> [-o <output_file>] [-c <chunks>] [-s <script>]"
  echo ""
  echo "  -i    Path to input file with URLs (required)"
  echo "  -r    Result base directory (required)"
  echo "  -o    Output file path (optional, default: <result_dir>/endpoint_active.txt)"
  echo "  -c    Number of parallel chunks (default: 2)"
  echo "  -s    Python script to execute (default: ./parse_endpoint.py)"
  exit 1
}

# Parse arguments
while getopts "i:c:s:r:o:" opt; do
  case "$opt" in
    i) INPUT_FILE="$OPTARG" ;;
    c) CHUNKS="$OPTARG" ;;
    s) SCRIPT="$OPTARG" ;;
    r) RESULT_DIR="$OPTARG" ;;
    o) OUTPUT_FILE="$OPTARG" ;;
    *) print_usage ;;
  esac
done

# Validate required arguments
if [[ -z "$INPUT_FILE" || -z "$SCRIPT" || -z "$RESULT_DIR" ]]; then
  echo "[!] Missing required arguments."
  print_usage
fi

# Derived paths
TEMP_DIR="$RESULT_DIR/temp_chunks"
FINAL_OUTPUT="${OUTPUT_FILE:-$RESULT_DIR/endpoints_active.txt}"

# Trap Ctrl+C
trap 'echo "[!] Script interrupted. Cleaning up..."; rm -rf "$TEMP_DIR"; exit 1' INT

# Create temp working dir
mkdir -p "$TEMP_DIR"

# Split the input into chunks
split -n l/"$CHUNKS" "$INPUT_FILE" "$TEMP_DIR/chunk_"

# Launch processing for each chunk
i=1
for chunk in "$TEMP_DIR"/chunk_*; do
  chunk_name=$(basename "$chunk")
  echo "[*] Starting process $i for $chunk_name"

  python3 "$SCRIPT" -i "$chunk" -o "$TEMP_DIR/output_$chunk_name.txt" --html-dump-dir "$RESULT_DIR/html"  \
    > "$TEMP_DIR/log_$chunk_name.txt" 2>&1 &

  ((i++))
done

# Wait for all background jobs to finish
wait
echo "[+] All processes finished."

# Merge output results
cat "$TEMP_DIR"/output_chunk_*.txt > "$FINAL_OUTPUT"
echo "[+] Merged output written to $FINAL_OUTPUT"

# Clean up
# rm -r "$TEMP_DIR"
echo "[+] Temporary files cleaned up."
