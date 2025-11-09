#!/usr/bin/env python3
"""
Churn Prediction System - Startup Script (Python)
Starts all required services for the system.
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# Create logs directory
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# PIDs storage
PIDS_FILE = LOGS_DIR / "pids.txt"

def print_step(step_num, message):
    """Print formatted step message."""
    print(f"\n📦 Step {step_num}: {message}")

def print_success(message):
    """Print success message."""
    print(f"✅ {message}")

def print_error(message):
    """Print error message."""
    print(f"❌ {message}")

def check_docker():
    """Check if Docker is available."""
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
        subprocess.run(["docker-compose", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def start_docker_services():
    """Start Docker services (Kafka, Redis, Zookeeper)."""
    print_step(1, "Starting Docker services...")
    if not check_docker():
        print_error("Docker not found. Please install Docker and docker-compose.")
        return False
    
    try:
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        print_success("Docker services started")
        print("   Waiting 10 seconds for services to initialize...")
        time.sleep(10)
        return True
    except subprocess.CalledProcessError:
        print_error("Failed to start Docker services")
        return False

def run_migrations():
    """Run Django database migrations."""
    print_step(2, "Running database migrations...")
    try:
        subprocess.run([sys.executable, "manage.py", "migrate"], check=True)
        print_success("Database migrations complete")
        return True
    except subprocess.CalledProcessError:
        print_error("Failed to run migrations")
        return False

def create_superuser():
    """Create superuser if needed."""
    print_step(2.5, "Checking for superuser...")
    try:
        subprocess.run([sys.executable, "scripts/create_superuser.py"], check=True)
        return True
    except subprocess.CalledProcessError:
        print_error("Failed to create superuser (this is optional)")
        return False

def start_django():
    """Start Django development server."""
    print_step(3, "Starting Django server...")
    log_file = LOGS_DIR / "django.log"
    try:
        with open(log_file, "w") as f:
            process = subprocess.Popen(
                [sys.executable, "manage.py", "runserver"],
                stdout=f,
                stderr=subprocess.STDOUT
            )
            save_pid("django", process.pid)
            print_success(f"Django server started (PID: {process.pid})")
            print("   Access at: http://localhost:8000")
            print("   Dashboard: http://localhost:8000/analytics/churn-dashboard/")
            return True
    except Exception as e:
        print_error(f"Failed to start Django: {e}")
        return False

def start_collector():
    """Start FastAPI event collector."""
    print_step(4, "Starting FastAPI event collector...")
    log_file = LOGS_DIR / "collector.log"
    collector_dir = PROJECT_ROOT / "streaming" / "collectors"
    
    try:
        with open(log_file, "w") as f:
            process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "fastapi_collector:app", 
                 "--host", "0.0.0.0", "--port", "9000"],
                cwd=collector_dir,
                stdout=f,
                stderr=subprocess.STDOUT
            )
            save_pid("collector", process.pid)
            print_success(f"FastAPI collector started (PID: {process.pid})")
            print("   Access at: http://localhost:9000")
            return True
    except Exception as e:
        print_error(f"Failed to start collector: {e}")
        return False

def start_consumer():
    """Start Kafka consumer."""
    print_step(5, "Starting Kafka consumer...")
    log_file = LOGS_DIR / "consumer.log"
    consumer_script = PROJECT_ROOT / "streaming" / "consumers" / "django_consumer.py"
    
    try:
        with open(log_file, "w") as f:
            process = subprocess.Popen(
                [sys.executable, str(consumer_script)],
                stdout=f,
                stderr=subprocess.STDOUT
            )
            save_pid("consumer", process.pid)
            print_success(f"Kafka consumer started (PID: {process.pid})")
            return True
    except Exception as e:
        print_error(f"Failed to start consumer: {e}")
        return False

def save_pid(service, pid):
    """Save PID to file."""
    with open(PIDS_FILE, "a") as f:
        f.write(f"{service}:{pid}\n")

def main():
    """Main startup function."""
    print("🚀 Starting Churn Prediction System...")
    print("=" * 50)
    
    # Clear previous PIDs
    if PIDS_FILE.exists():
        PIDS_FILE.unlink()
    
    # Start services
    services_started = []
    
    if start_docker_services():
        services_started.append("Docker")
    
    if run_migrations():
        services_started.append("Migrations")
    
    create_superuser()  # Optional, won't fail if it doesn't work
    
    if start_django():
        services_started.append("Django")
    
    if start_collector():
        services_started.append("Collector")
    
    if start_consumer():
        services_started.append("Consumer")
    
    # Summary
    print("\n" + "=" * 50)
    print("✅ Startup Complete!")
    print("\n📊 Service Status:")
    print("   - Django: http://localhost:8000")
    print("   - FastAPI Collector: http://localhost:9000")
    print("   - Kafka Consumer: Running")
    print("\n📝 Logs:")
    print(f"   - Django: {LOGS_DIR / 'django.log'}")
    print(f"   - Collector: {LOGS_DIR / 'collector.log'}")
    print(f"   - Consumer: {LOGS_DIR / 'consumer.log'}")
    print("\n🛑 To stop services:")
    print("   - Press Ctrl+C and run: python scripts/stop_all.py")
    print("   - Or manually kill processes from logs/pids.txt")
    
    # Keep script running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        stop_all_services()

def stop_all_services():
    """Stop all running services."""
    if not PIDS_FILE.exists():
        print("No PIDs file found. Services may not be running.")
        return
    
    print("Stopping services...")
    with open(PIDS_FILE, "r") as f:
        for line in f:
            service, pid = line.strip().split(":")
            try:
                os.kill(int(pid), signal.SIGTERM)
                print(f"✅ Stopped {service} (PID: {pid})")
            except ProcessLookupError:
                print(f"⚠️  {service} (PID: {pid}) was not running")
            except Exception as e:
                print(f"❌ Error stopping {service}: {e}")
    
    # Stop Docker services
    try:
        subprocess.run(["docker-compose", "down"], check=True)
        print("✅ Docker services stopped")
    except:
        pass
    
    PIDS_FILE.unlink()
    print("✅ All services stopped")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        stop_all_services()

