#!/usr/bin/env python3
"""
Start Flink processing jobs.
These jobs run as Python processes using PyFlink (local execution mode).
"""

import os
import sys
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# Flink job scripts
FLINK_JOBS = {
    "churn_ml": "streaming/processors/flink_churn_ml_processor.py",
    "cart_abandon": "streaming/processors/flink_cart_processor.py",
    # "churn_basic": "streaming/processors/flink_churn_processor.py",  # Uncomment if needed
}

def start_flink_job(job_name, script_path):
    """Start a Flink job as a background process."""
    log_file = PROJECT_ROOT / "logs" / f"flink_{job_name}.log"
    log_file.parent.mkdir(exist_ok=True)
    
    try:
        with open(log_file, "w") as f:
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=PROJECT_ROOT
            )
        
        # Save PID
        pid_file = PROJECT_ROOT / "logs" / f"flink_{job_name}.pid"
        with open(pid_file, "w") as f:
            f.write(str(process.pid))
        
        print(f"✅ Started Flink job: {job_name} (PID: {process.pid})")
        print(f"   Log: {log_file}")
        return process.pid
    except Exception as e:
        print(f"❌ Failed to start Flink job {job_name}: {e}")
        return None

def main():
    """Start all Flink jobs."""
    print("🚀 Starting Flink Processing Jobs...")
    print("=" * 50)
    
    # Check if Flink jobs should be started
    start_flink = os.getenv("START_FLINK_JOBS", "true").lower() in ("true", "1", "yes")
    
    if not start_flink:
        print("⚠️  Flink jobs disabled (set START_FLINK_JOBS=true to enable)")
        return
    
    pids = []
    
    for job_name, script_path in FLINK_JOBS.items():
        script = PROJECT_ROOT / script_path
        if not script.exists():
            print(f"⚠️  Flink job script not found: {script_path}")
            continue
        
        pid = start_flink_job(job_name, script_path)
        if pid:
            pids.append((job_name, pid))
        time.sleep(2)  # Stagger startup
    
    if pids:
        print("\n" + "=" * 50)
        print("✅ Flink Jobs Started:")
        for job_name, pid in pids:
            print(f"   - {job_name}: PID {pid}")
        print("\n📝 Logs:")
        for job_name, _ in pids:
            print(f"   - {job_name}: logs/flink_{job_name}.log")
        print("\n🛑 To stop Flink jobs:")
        print("   python scripts/stop_flink_jobs.py")
    else:
        print("❌ No Flink jobs started")

if __name__ == "__main__":
    main()

