#!/bin/bash

# --------- CONFIGURATION ----------
INPUT_FILE="./results/heartology.id/endpoints.txt"           # Input file with URLs
CHUNKS=1                                                     # Number of parallel processes
SCRIPT="./scripts/parse_endpoint.py"                         # Your Python script
RESULT_DIR="./results/heartology.id"                         # Result base directory
TEMP_DIR="$RESULT_DIR/temp_chunks"                           # Temporary working directory
FINAL_OUTPUT="$RESULT_DIR/endpoint_active.txt"               # Final merged output
# ----------------------------------

trap 'echo "[!] Script interrupted. Cleaning up..."; rm -rf "$TEMP_DIR"; exit 1' INT

# Create temp output directory
mkdir -p "$TEMP_DIR"

# Split input into chunks inside temp dir
split -n l/$CHUNKS "$INPUT_FILE" "$TEMP_DIR/chunk_"

# Launch each chunk in background
i=1
for chunk in "$TEMP_DIR"/chunk_*; do
  chunk_name=$(basename "$chunk")
  echo "[*] Starting process $i for $chunk_name"
  
  python3 "$SCRIPT" -i "$chunk" -o "$TEMP_DIR/output_$chunk_name.txt" 2>&1 | tee "$TEMP_DIR/log_$chunk_name.txt"

  ((i++))
done

# Wait for all background jobs
wait
echo "[+] All processes finished."

# Merge all outputs
cat "$TEMP_DIR"/output_chunk_*.txt > "$FINAL_OUTPUT"
echo "[+] Merged output written to $FINAL_OUTPUT"

# Optionally clean up
rm -r "$TEMP_DIR"
echo "[+] Temporary files cleaned up."
