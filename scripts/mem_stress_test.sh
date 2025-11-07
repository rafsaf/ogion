#!/usr/bin/env bash
# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

set -euo pipefail

# Configuration - only accept BACKUP_PROVIDER_NAME and STRESS_ITERATIONS from environment
ITERATIONS="${STRESS_ITERATIONS:-10}"
PROVIDER="${BACKUP_PROVIDER_NAME:-debug}"
MEMORY_LOG="/tmp/ogion_stress_memory.log"
RESULTS_LOG="/tmp/ogion_stress_results.log"
MEMORY_MONITOR_SCRIPT="/tmp/ogion_memory_monitor.py"

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

# Setup storage buckets/containers for providers
echo -e "${YELLOW}Setting up storage...${NC}"
case "$PROVIDER" in
    gcs)
        # GCS fake server auto-creates buckets
        echo "  GCS: Using fake-gcs-server (auto-creates buckets)"
        ;;
    s3)
        # Create MinIO bucket using mc (MinIO Client)
        echo "  S3: Creating bucket 'stresstest' in MinIO..."
        # Use Python with minio library since it's already available
        /opt/venv/bin/python3 << 'SETUP_S3'
from minio import Minio

client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

bucket_name = "stresstest"
if not client.bucket_exists(bucket_name):
    client.make_bucket(bucket_name)
    print(f"  Created bucket: {bucket_name}")
else:
    print(f"  Bucket already exists: {bucket_name}")
SETUP_S3
        ;;
    azure)
        # Create Azure container
        echo "  Azure: Creating container 'stresstest'..."
        /opt/venv/bin/python3 << 'SETUP_AZURE'
from azure.storage.blob import BlobServiceClient

connect_string = (
    "DefaultEndpointsProtocol=http;"
    "AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
    "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
)

blob_service_client = BlobServiceClient.from_connection_string(connect_string)
container_name = "stresstest"
try:
    container_client = blob_service_client.create_container(container_name)
    print(f"  Created container: {container_name}")
except Exception as e:
    if "ContainerAlreadyExists" in str(e):
        print(f"  Container already exists: {container_name}")
    else:
        raise
SETUP_AZURE
        ;;
    debug)
        echo "  Debug: Using local filesystem (no setup needed)"
        ;;
esac
echo ""

# Clean up old logs
rm -f "$MEMORY_LOG" "$RESULTS_LOG"

# Create Python-based memory monitor that uses psutil for accurate tracking
cat > "$MEMORY_MONITOR_SCRIPT" << 'PYTHON_SCRIPT'
#!/opt/venv/bin/python3
import sys
import time
import psutil
import csv

def monitor_memory(pid, log_file, sample_interval=0.1):
    """Monitor memory usage of a process using psutil."""
    try:
        process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        print(f"Process {pid} not found", file=sys.stderr)
        sys.exit(1)
    
    with open(log_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'iteration', 'rss_mb', 'vms_mb', 'num_fds'])
        
        start_time = time.time()
        sample_count = 0
        
        while process.is_running():
            try:
                # Get memory info
                mem_info = process.memory_info()
                rss_mb = mem_info.rss / (1024 * 1024)
                vms_mb = mem_info.vms / (1024 * 1024)
                
                # Get file descriptors count (can indicate resource leaks)
                try:
                    num_fds = process.num_fds()
                except (AttributeError, psutil.AccessDenied):
                    num_fds = -1
                
                # Try to get current iteration
                iteration = "N/A"
                try:
                    with open("/tmp/ogion_current_iteration.txt", 'r') as iter_f:
                        iteration = iter_f.read().strip()
                except:
                    pass
                
                elapsed = time.time() - start_time
                writer.writerow([f"{elapsed:.2f}", iteration, f"{rss_mb:.2f}", 
                                f"{vms_mb:.2f}", num_fds])
                f.flush()
                
                sample_count += 1
                if sample_count % 50 == 0:
                    print(f"[MEMORY] RSS: {rss_mb:.1f}MB, VMS: {vms_mb:.1f}MB, "
                          f"FDs: {num_fds}, Iter: {iteration}", file=sys.stderr)
                
                time.sleep(sample_interval)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            except KeyboardInterrupt:
                break

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: monitor_memory.py <pid> <log_file>", file=sys.stderr)
        sys.exit(1)
    
    pid = int(sys.argv[1])
    log_file = sys.argv[2]
    monitor_memory(pid, log_file)
PYTHON_SCRIPT

chmod +x "$MEMORY_MONITOR_SCRIPT"

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

# Start memory monitoring in background using Python script (use venv python)
/opt/venv/bin/python3 "$MEMORY_MONITOR_SCRIPT" "$OGION_PID" "$MEMORY_LOG" &
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
    
    # Use Python for sophisticated analysis (use venv python)
    /opt/venv/bin/python3 << 'PYTHON_ANALYSIS'
import csv
import sys
from pathlib import Path

log_file = Path("/tmp/ogion_stress_memory.log")
if not log_file.exists():
    print("No memory log found")
    sys.exit(1)

# Read all memory samples
samples = []
with open(log_file) as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            samples.append({
                'timestamp': float(row['timestamp']),
                'iteration': row['iteration'],
                'rss_mb': float(row['rss_mb']),
                'vms_mb': float(row['vms_mb']),
                'num_fds': int(row['num_fds']) if row['num_fds'] != '-1' else -1
            })
        except (ValueError, KeyError):
            continue

if len(samples) < 10:
    print(f"Not enough samples: {len(samples)}")
    sys.exit(1)

# Calculate statistics
total_samples = len(samples)
initial_samples = samples[int(total_samples * 0.45):int(total_samples * 0.55)]  # Mid 45-55%
final_samples = samples[-max(10, int(total_samples * 0.1)):]    # Last 10%

initial_rss = sum(s['rss_mb'] for s in initial_samples) / len(initial_samples)
final_rss = sum(s['rss_mb'] for s in final_samples) / len(final_samples)
peak_rss = max(s['rss_mb'] for s in samples)
min_rss = min(s['rss_mb'] for s in samples)

growth_mb = final_rss - initial_rss
growth_pct = (growth_mb / initial_rss * 100) if initial_rss > 0 else 0

print(f"  Total samples:  {total_samples}")
print(f"  Baseline RSS:   {initial_rss:.2f}MB (avg of mid {len(initial_samples)} samples, 45-55%)")
print(f"  Final RSS:      {final_rss:.2f}MB (avg of last {len(final_samples)} samples)")
print(f"  Peak RSS:       {peak_rss:.2f}MB")
print(f"  Min RSS:        {min_rss:.2f}MB")
print(f"  Growth:         {growth_mb:+.2f}MB ({growth_pct:+.1f}%)")

# Check file descriptors if available
if samples[0]['num_fds'] != -1 and samples[-1]['num_fds'] != -1:
    initial_fds = sum(s['num_fds'] for s in initial_samples if s['num_fds'] != -1) / len([s for s in initial_samples if s['num_fds'] != -1])
    final_fds = sum(s['num_fds'] for s in final_samples if s['num_fds'] != -1) / len([s for s in final_samples if s['num_fds'] != -1])
    fd_growth = final_fds - initial_fds
    print(f"  Baseline FDs:   {initial_fds:.0f}")
    print(f"  Final FDs:      {final_fds:.0f}")
    print(f"  FD Growth:      {fd_growth:+.0f}")
else:
    fd_growth = 0

# Linear regression to detect trend
import statistics
if len(samples) >= 20:
    # Use middle 80% of samples to avoid startup/shutdown noise
    start_idx = int(total_samples * 0.1)
    end_idx = int(total_samples * 0.9)
    stable_samples = samples[start_idx:end_idx]
    
    if len(stable_samples) >= 10:
        # Simple linear regression
        x_vals = list(range(len(stable_samples)))
        y_vals = [s['rss_mb'] for s in stable_samples]
        
        n = len(x_vals)
        sum_x = sum(x_vals)
        sum_y = sum(y_vals)
        sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
        sum_x2 = sum(x * x for x in x_vals)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Estimate MB leaked per 100 samples
        leak_rate_per_100 = slope * 100
        print(f"  Leak rate:      {leak_rate_per_100:+.3f}MB per 100 samples")
        
        # Detect leak based on slope
        is_leaking = abs(leak_rate_per_100) > 0.5  # More than 0.5MB per 100 samples
    else:
        is_leaking = False
        leak_rate_per_100 = 0
else:
    is_leaking = False
    leak_rate_per_100 = 0

print()

# Determine leak status
LEAK_THRESHOLD_PCT = 10  # 10% growth
LEAK_THRESHOLD_MB = 20   # 20MB absolute growth
FD_LEAK_THRESHOLD = 50   # 50 file descriptors

leak_detected = False
leak_reasons = []

if growth_mb > LEAK_THRESHOLD_MB:
    leak_detected = True
    leak_reasons.append(f"Memory grew by {growth_mb:.1f}MB (threshold: {LEAK_THRESHOLD_MB}MB)")

if growth_pct > LEAK_THRESHOLD_PCT:
    leak_detected = True
    leak_reasons.append(f"Memory grew by {growth_pct:.1f}% (threshold: {LEAK_THRESHOLD_PCT}%)")

if fd_growth > FD_LEAK_THRESHOLD:
    leak_detected = True
    leak_reasons.append(f"File descriptors grew by {fd_growth:.0f} (threshold: {FD_LEAK_THRESHOLD})")

if is_leaking and abs(leak_rate_per_100) > 1.0:
    leak_detected = True
    leak_reasons.append(f"Linear growth detected: {leak_rate_per_100:+.3f}MB per 100 samples")

if leak_detected:
    print("\033[0;31m⚠️  MEMORY LEAK DETECTED!\033[0m")
    print("\033[0;31mReasons:\033[0m")
    for reason in leak_reasons:
        print(f"\033[0;31m  • {reason}\033[0m")
    sys.exit(2)  # Exit code 2 = leak detected
else:
    print("\033[0;32m✓ Memory usage appears stable\033[0m")
    print(f"\033[0;32m  Growth: {growth_mb:+.2f}MB ({growth_pct:+.1f}%)\033[0m")
    if leak_rate_per_100 != 0:
        print(f"\033[0;32m  Trend: {leak_rate_per_100:+.3f}MB per 100 samples\033[0m")
    sys.exit(0)
PYTHON_ANALYSIS
    
    ANALYSIS_EXIT_CODE=$?
    
    echo ""
    echo -e "${GREEN}Detailed Memory Log:${NC} $MEMORY_LOG"
    ANALYSIS_EXIT_CODE=$?
    
    echo ""
    echo -e "${GREEN}Detailed Memory Log:${NC} $MEMORY_LOG"
else
    echo -e "${YELLOW}No memory data collected${NC}"
    ANALYSIS_EXIT_CODE=1
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"

# Exit with appropriate code
# 0 = success, no leak
# 1 = execution failure
# 2 = leak detected
if [ "$EXIT_CODE" -ne 0 ]; then
    exit "$EXIT_CODE"
elif [ "${ANALYSIS_EXIT_CODE:-1}" -eq 2 ]; then
    echo -e "${RED}FAIL: Memory leak detected${NC}"
    exit 2
else
    exit 0
fi
