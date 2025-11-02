#!/usr/bin/env bash
# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

set -euo pipefail

# Configuration - only accept PROVIDER and STRESS_ITERATIONS from environment
ITERATIONS="${STRESS_ITERATIONS:-10}"
PROVIDER="${PROVIDER:-debug}"
MEMORY_SAMPLE_INTERVAL=1  # seconds - hardcoded
MEMORY_LOG="/tmp/ogion_stress_memory.log"
RESULTS_LOG="/tmp/ogion_stress_results.log"

# Hardcoded provider configurations
GCS_PROVIDER="name=gcs bucket_name=stresstest bucket_upload_path=test service_account_base64=Z29vZ2xlX3NlcnZpY2VfYWNjb3VudAo="
S3_PROVIDER="name=s3 endpoint=localhost:9000 bucket_name=stresstest access_key=minioadmin secret_key=minioadmin bucket_upload_path=test secure=false"
AZURE_PROVIDER="name=azure container_name=stresstest connect_string=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
DEBUG_PROVIDER="name=debug"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         OGION STRESS TEST - MEMORY LEAK DETECTION               ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Iterations: $ITERATIONS"
echo "  Provider: $PROVIDER"
echo "  Memory sample interval: ${MEMORY_SAMPLE_INTERVAL}s"
echo "  Memory log: $MEMORY_LOG"
echo "  Results log: $RESULTS_LOG"
echo ""

# Configure provider-specific environment variables
case "$PROVIDER" in
    gcs)
        echo -e "${YELLOW}Configuring GCS provider (fake-gcs-server)...${NC}"
        export STORAGE_EMULATOR_HOST="http://localhost:4443"
        export BACKUP_PROVIDER="$GCS_PROVIDER"
        ;;
    s3)
        echo -e "${YELLOW}Configuring S3 provider (MinIO)...${NC}"
        export BACKUP_PROVIDER="$S3_PROVIDER"
        ;;
    azure)
        echo -e "${YELLOW}Configuring Azure provider (Azurite)...${NC}"
        export BACKUP_PROVIDER="$AZURE_PROVIDER"
        ;;
    debug)
        echo -e "${YELLOW}Using debug provider (local filesystem)...${NC}"
        export BACKUP_PROVIDER="$DEBUG_PROVIDER"
        ;;
    *)
        echo -e "${RED}Error: Unknown provider '$PROVIDER'${NC}"
        echo "Supported providers: gcs, s3, azure, debug"
        exit 1
        ;;
esac
echo ""

# Clean up old logs
rm -f "$MEMORY_LOG" "$RESULTS_LOG"

# Memory monitoring function
monitor_memory() {
    local pid=$1
    echo "timestamp_sec,iteration,rss_kb,vms_kb,rss_mb" > "$MEMORY_LOG"
    
    local start_time=$(date +%s)
    local sample_count=0
    
    while kill -0 "$pid" 2>/dev/null; do
        if [ -f "/proc/$pid/status" ]; then
            local current_time=$(date +%s)
            local elapsed=$((current_time - start_time))
            
            # Extract memory metrics from /proc/PID/status
            local vmrss=$(grep "^VmRSS:" "/proc/$pid/status" | awk '{print $2}')
            local vmsize=$(grep "^VmSize:" "/proc/$pid/status" | awk '{print $2}')
            
            # Calculate RSS in MB for easier reading
            local rss_mb=$(awk "BEGIN {printf \"%.2f\", $vmrss/1024}")
            
            # Try to extract current iteration from logs (approximate)
            local iteration="N/A"
            if [ -f "/tmp/ogion_current_iteration.txt" ]; then
                iteration=$(cat /tmp/ogion_current_iteration.txt 2>/dev/null || echo "N/A")
            fi
            
            echo "$elapsed,$iteration,$vmrss,$vmsize,$rss_mb" >> "$MEMORY_LOG"
            
            ((sample_count++))
            if [ $((sample_count % 30)) -eq 0 ]; then
                echo -e "${BLUE}[MEMORY]${NC} RSS: ${rss_mb}MB, VmSize: $((vmsize/1024))MB (sample $sample_count)"
            fi
        fi
        sleep "$MEMORY_SAMPLE_INTERVAL"
    done
}

# Prepare test environment
echo -e "${YELLOW}Preparing test environment...${NC}"

# Create a helper to track iterations (ogion will write to this)
export STRESS_TEST_ITERATION_FILE="/tmp/ogion_current_iteration.txt"
echo "0" > "$STRESS_TEST_ITERATION_FILE"

# Start ogion with debug-loop mode
echo -e "${GREEN}Starting Ogion in debug-loop mode...${NC}"
echo ""

# Build command - simplified, no TARGET support
CMD="ogion --debug-loop $ITERATIONS"

echo -e "${BLUE}Command: $CMD${NC}"
echo ""

# Start ogion in background and capture PID
START_TIME=$(date +%s)
$CMD &
OGION_PID=$!

echo -e "${GREEN}Ogion started with PID: $OGION_PID${NC}"
echo ""

# Start memory monitoring in background
monitor_memory "$OGION_PID" &
MONITOR_PID=$!

# Wait for ogion to complete
if wait "$OGION_PID"; then
    EXIT_CODE=0
    echo -e "${GREEN}✓ Ogion completed successfully${NC}"
else
    EXIT_CODE=$?
    echo -e "${RED}✗ Ogion failed with exit code: $EXIT_CODE${NC}"
fi

# Stop memory monitoring
kill "$MONITOR_PID" 2>/dev/null || true
wait "$MONITOR_PID" 2>/dev/null || true

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                      STRESS TEST RESULTS                         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Execution Summary:${NC}"
echo "  Duration: ${DURATION}s ($(awk "BEGIN {printf \"%.2f\", $DURATION/60}") minutes)"
echo "  Provider: $PROVIDER"
echo "  Exit code: $EXIT_CODE"
echo ""

# Analyze memory usage
if [ -f "$MEMORY_LOG" ] && [ "$(wc -l < "$MEMORY_LOG")" -gt 1 ]; then
    echo -e "${GREEN}Memory Analysis:${NC}"
    
    # Skip header, get stats
    MEMORY_DATA=$(tail -n +2 "$MEMORY_LOG")
    
    # Initial memory (from first 5 samples average)
    INITIAL_RSS=$(echo "$MEMORY_DATA" | head -n 5 | awk -F',' '{sum+=$3; count++} END {printf "%.0f", sum/count}')
    INITIAL_RSS_MB=$(awk "BEGIN {printf \"%.2f\", $INITIAL_RSS/1024}")
    
    # Peak memory
    PEAK_RSS=$(echo "$MEMORY_DATA" | awk -F',' '{if($3>max)max=$3} END {print max}')
    PEAK_RSS_MB=$(awk "BEGIN {printf \"%.2f\", $PEAK_RSS/1024}")
    
    # Final memory (from last 5 samples average)
    FINAL_RSS=$(echo "$MEMORY_DATA" | tail -n 5 | awk -F',' '{sum+=$3; count++} END {printf "%.0f", sum/count}')
    FINAL_RSS_MB=$(awk "BEGIN {printf \"%.2f\", $FINAL_RSS/1024}")
    
    # Calculate memory growth
    GROWTH_KB=$((FINAL_RSS - INITIAL_RSS))
    GROWTH_MB=$(awk "BEGIN {printf \"%.2f\", $GROWTH_KB/1024}")
    GROWTH_PCT=$(awk "BEGIN {if($INITIAL_RSS>0) printf \"%.1f\", ($GROWTH_KB/$INITIAL_RSS)*100; else print \"N/A\"}")
    
    echo "  Initial RSS:  ${INITIAL_RSS_MB}MB"
    echo "  Peak RSS:     ${PEAK_RSS_MB}MB"
    echo "  Final RSS:    ${FINAL_RSS_MB}MB"
    echo "  Growth:       ${GROWTH_MB}MB (${GROWTH_PCT}%)"
    echo ""
    
    # Memory leak detection logic
    LEAK_THRESHOLD_PCT=20  # Consider it a leak if growth > 20%
    LEAK_THRESHOLD_MB=50   # Or absolute growth > 50MB
    
    if [ "$EXIT_CODE" -eq 0 ]; then
        # Check for memory leak
        if [ "$(echo "$GROWTH_PCT > $LEAK_THRESHOLD_PCT" | bc -l 2>/dev/null || echo 0)" -eq 1 ] || \
           [ "$(echo "$GROWTH_MB > $LEAK_THRESHOLD_MB" | bc -l 2>/dev/null || echo 0)" -eq 1 ]; then
            echo -e "${RED}⚠ WARNING: Potential memory leak detected!${NC}"
            echo -e "${RED}  Memory grew by ${GROWTH_MB}MB (${GROWTH_PCT}%)${NC}"
            echo -e "${YELLOW}  Threshold: ${LEAK_THRESHOLD_PCT}% or ${LEAK_THRESHOLD_MB}MB${NC}"
            LEAK_STATUS="POTENTIAL_LEAK"
        else
            echo -e "${GREEN}✓ Memory usage appears stable (growth: ${GROWTH_MB}MB, ${GROWTH_PCT}%)${NC}"
            LEAK_STATUS="STABLE"
        fi
    else
        echo -e "${YELLOW}! Cannot determine memory leak status due to execution failure${NC}"
        LEAK_STATUS="UNKNOWN_DUE_TO_FAILURE"
    fi
    
    echo ""
    echo -e "${GREEN}Detailed Memory Log:${NC} $MEMORY_LOG"
    echo "  Samples collected: $(tail -n +2 "$MEMORY_LOG" | wc -l)"
    
    # Save summary to results log
    {
        echo "=== OGION STRESS TEST RESULTS ==="
        echo "Date: $(date)"
        echo "Iterations: $ITERATIONS"
        echo "Provider: $PROVIDER"
        echo "Duration: ${DURATION}s"
        echo "Exit Code: $EXIT_CODE"
        echo ""
        echo "=== MEMORY ANALYSIS ==="
        echo "Initial RSS: ${INITIAL_RSS_MB}MB"
        echo "Peak RSS: ${PEAK_RSS_MB}MB"
        echo "Final RSS: ${FINAL_RSS_MB}MB"
        echo "Growth: ${GROWTH_MB}MB (${GROWTH_PCT}%)"
        echo "Status: $LEAK_STATUS"
        echo ""
        echo "Memory log: $MEMORY_LOG"
        echo "Samples: $(tail -n +2 "$MEMORY_LOG" | wc -l)"
    } > "$RESULTS_LOG"
    
    echo -e "${GREEN}Summary saved to:${NC} $RESULTS_LOG"
else
    echo -e "${YELLOW}No memory data collected${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"

# Exit with ogion's exit code
exit $EXIT_CODE
