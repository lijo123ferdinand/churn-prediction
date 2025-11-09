#!/usr/bin/env python3
"""
Churn Prediction System - Stop Script (Python)
Stops all running services.
"""

import os
import subprocess
import signal
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PIDS_FILE = PROJECT_ROOT / "logs" / "pids.txt"

def stop_all_services():
    """Stop all running services."""
    print("🛑 Stopping Churn Prediction System...")
    print("=" * 50)
    
    # Stop services by PID
    if PIDS_FILE.exists():
        print("\nStopping application services...")
        with open(PIDS_FILE, "r") as f:
            for line in f:
                if ":" in line:
                    service, pid = line.strip().split(":")
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        print(f"✅ Stopped {service} (PID: {pid})")
                    except ProcessLookupError:
                        print(f"⚠️  {service} (PID: {pid}) was not running")
                    except Exception as e:
                        print(f"❌ Error stopping {service}: {e}")
        PIDS_FILE.unlink()
    else:
        print("⚠️  No PIDs file found. Services may not be running.")
    
    # Stop Docker services
    print("\nStopping Docker services...")
    try:
        subprocess.run(["docker-compose", "down"], check=True)
        print("✅ Docker services stopped")
    except subprocess.CalledProcessError:
        print("⚠️  Failed to stop Docker services")
    except FileNotFoundError:
        print("⚠️  docker-compose not found")
    
    print("\n✅ All services stopped")

if __name__ == "__main__":
    stop_all_services()

