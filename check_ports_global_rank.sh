#!/usr/bin/env bash
# check_ports_global_rank.sh
# Show GLOBAL RAM rank + actual RAM usage + % of total RAM
# for processes listening on important ports.

set -euo pipefail

PORTS=(9000 8000 8081 2181 5432 6380 9092)

# --- Get total memory in KB ---
TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_RAM_MB=$((TOTAL_RAM_KB / 1024))

echo "Collecting GLOBAL RAM ranking..."
echo "-----------------------------------------------"

# Get ALL running processes sorted by memory (RSS)
# Format: rank:pid:process:rss
mapfile -t ALL_PROCS < <(
  ps -eo pid,comm,rss --sort=-rss \
  | awk 'NR>1 {print NR-1 ":" $1 ":" $2 ":" $3}'
)

declare -A GLOBAL_RANK
declare -A RSS_MAP
declare -A NAME_MAP

# Build mapping: PID → rank, RSS, process-name
for entry in "${ALL_PROCS[@]}"; do
  rank=$(echo "$entry" | cut -d: -f1)
  pid=$(echo "$entry" | cut -d: -f2)
  name=$(echo "$entry" | cut -d: -f3)
  rss=$(echo "$entry" | cut -d: -f4)

  GLOBAL_RANK["$pid"]="$rank"
  RSS_MAP["$pid"]="$rss"
  NAME_MAP["$pid"]="$name"
done

echo "Checking ports..."
echo "--------------------------------------------------------------------------"
printf "%-6s %-8s %-18s %-12s %-12s %-10s\n" \
  "PORT" "PID" "PROCESS" "GLOBAL-RANK" "RAM(MB)" "RAM(%)"
echo "--------------------------------------------------------------------------"

for port in "${PORTS[@]}"; do
  result=$(sudo lsof -iTCP:$port -sTCP:LISTEN -n -P 2>/dev/null || true)

  if [[ -z "$result" ]]; then
    printf "%-6s %-8s %-18s %-12s %-12s %-10s\n" "$port" "-" "FREE" "-" "-" "-"
    continue
  fi

  pid=$(echo "$result" | awk 'NR==2 {print $2}')

  process="${NAME_MAP[$pid]:-unknown}"
  rank="${GLOBAL_RANK[$pid]:-NOT_FOUND}"
  rss_kb="${RSS_MAP[$pid]:-0}"
  rss_mb=$((rss_kb / 1024))

  ram_percent=$(awk -v r="$rss_kb" -v t="$TOTAL_RAM_KB" 'BEGIN {printf "%.2f", (r/t)*100}')

  printf "%-6s %-8s %-18s %-12s %-12s %-10s\n" \
    "$port" "$pid" "$process" "$rank" "${rss_mb}MB" "${ram_percent}%"
done

echo "--------------------------------------------------------------------------"

