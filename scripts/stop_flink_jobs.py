#!/usr/bin/env python3
"""
Stop all running Flink jobs.
"""

import os
import signal
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"

def stop_flink_jobs():
    """Stop all Flink jobs by PID."""
    print("🛑 Stopping Flink Jobs...")
    print("=" * 50)
    
    if not LOGS_DIR.exists():
        print("⚠️  No logs directory found. Flink jobs may not be running.")
        return
    
    stopped = 0
    pid_files = list(LOGS_DIR.glob("flink_*.pid"))
    
    if not pid_files:
        print("⚠️  No Flink job PIDs found.")
        return
    
    for pid_file in pid_files:
        job_name = pid_file.stem.replace("flink_", "").replace(".pid", "")
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
            
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"✅ Stopped {job_name} (PID: {pid})")
                stopped += 1
            except ProcessLookupError:
                print(f"⚠️  {job_name} (PID: {pid}) was not running")
            except Exception as e:
                print(f"❌ Error stopping {job_name}: {e}")
            
            pid_file.unlink()
        except Exception as e:
            print(f"❌ Error reading PID file {pid_file}: {e}")
    
    if stopped > 0:
        print(f"\n✅ Stopped {stopped} Flink job(s)")
    else:
        print("\n⚠️  No Flink jobs were running")

if __name__ == "__main__":
    stop_flink_jobs()

