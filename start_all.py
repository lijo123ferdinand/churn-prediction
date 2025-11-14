#!/usr/bin/env python3
"""
Start All Services Script
Starts all components of the churn prediction system:
- Docker services (Zookeeper, Kafka, Redis, PostgreSQL)
- Django server
- FastAPI event collector
- Kafka consumers (user events and cart events)
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path
from typing import List, Optional

# ANSI color codes for better output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_status(message: str, color: str = Colors.RESET):
    """Print colored status message."""
    print(f"{color}{Colors.BOLD}[*]{Colors.RESET} {color}{message}{Colors.RESET}")


def print_success(message: str):
    """Print success message."""
    print_status(message, Colors.GREEN)


def print_error(message: str):
    """Print error message."""
    print_status(message, Colors.RED)


def print_warning(message: str):
    """Print warning message."""
    print_status(message, Colors.YELLOW)


def print_info(message: str):
    """Print info message."""
    print_status(message, Colors.CYAN)


class ServiceManager:
    """Manages all services for the churn prediction system."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.processes: List[subprocess.Popen] = []
        self.threads: List[threading.Thread] = []
        self.running = True
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print_warning("\n🛑 Shutting down all services...")
        self.running = False
        self.stop_all()
        sys.exit(0)
    
    def check_docker(self) -> bool:
        """Check if Docker is installed and running."""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print_success(f"Docker found: {result.stdout.strip()}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        print_error("Docker is not installed or not running!")
        return False
    
    def check_docker_compose(self) -> bool:
        """Check if docker-compose is available."""
        try:
            # Try docker compose (newer) first
            result = subprocess.run(
                ['docker', 'compose', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.compose_cmd = ['docker', 'compose']
                print_success(f"Docker Compose found: {result.stdout.strip()}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Try docker-compose (older standalone)
        try:
            result = subprocess.run(
                ['docker-compose', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.compose_cmd = ['docker-compose']
                print_success(f"Docker Compose found: {result.stdout.strip()}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        print_error("Docker Compose is not installed!")
        return False
    
    def start_docker_services(self) -> bool:
        """Start Docker services using docker-compose."""
        print_info("Starting Docker services (Zookeeper, Kafka, Redis, PostgreSQL)...")
        
        compose_file = self.project_root / 'docker-compose.yml'
        if not compose_file.exists():
            print_error(f"Docker compose file not found: {compose_file}")
            return False
        
        try:
            # Start services in detached mode
            cmd = self.compose_cmd + ['-f', str(compose_file), 'up', '-d']
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print_success("Docker services started successfully")
                return True
            else:
                print_error(f"Failed to start Docker services: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print_error("Timeout starting Docker services")
            return False
        except Exception as e:
            print_error(f"Error starting Docker services: {e}")
            return False
    
    def wait_for_service(self, host: str, port: int, service_name: str, timeout: int = 60) -> bool:
        """Wait for a service to be ready by checking if port is open."""
        import socket
        
        print_info(f"Waiting for {service_name} on {host}:{port}...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    print_success(f"{service_name} is ready!")
                    return True
            except Exception:
                pass
            
            time.sleep(2)
        
        print_warning(f"{service_name} did not become ready within {timeout} seconds")
        return False
    
    def wait_for_docker_services(self):
        """Wait for all Docker services to be ready."""
        print_info("Waiting for Docker services to be ready...")
        
        services = [
            ('localhost', 2181, 'Zookeeper'),
            ('localhost', 9092, 'Kafka'),
            ('localhost', 6380, 'Redis'),
            ('localhost', 5432, 'PostgreSQL'),
            ('localhost', 8081, 'Flink JobManager'),
        ]
        
        for host, port, name in services:
            self.wait_for_service(host, port, name, timeout=90)
            time.sleep(2)  # Small delay between checks
        
        # Extra wait for Kafka to fully initialize
        if any(name == 'Kafka' for _, _, name in services):
            print_info("Waiting for Kafka to fully initialize...")
            time.sleep(5)
        
        # Extra wait for Flink to fully initialize
        if any(name == 'Flink JobManager' for _, _, name in services):
            print_info("Waiting for Flink to fully initialize...")
            time.sleep(10)
    
    def get_kafka_container_name(self) -> Optional[str]:
        """Get the Kafka container name from docker-compose."""
        try:
            compose_file = self.project_root / 'docker-compose.yml'
            # Get container name using docker compose ps
            cmd = self.compose_cmd + ['-f', str(compose_file), 'ps', '-q', 'kafka']
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                container_id = result.stdout.strip()
                # Get container name from ID
                cmd2 = ['docker', 'inspect', '--format', '{{.Name}}', container_id]
                result2 = subprocess.run(
                    cmd2,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result2.returncode == 0:
                    return result2.stdout.strip().lstrip('/')
        except Exception as e:
            print_warning(f"Could not get Kafka container name: {e}")
        return None
    
    def create_kafka_topics(self):
        """Create required Kafka topics if they don't exist."""
        print_info("Creating Kafka topics...")
        
        topics = [
            ('user_events', 3),
            ('cart_events', 3),
        ]
        
        compose_file = self.project_root / 'docker-compose.yml'
        
        for topic_name, partitions in topics:
            try:
                # Check if topic exists
                cmd_check = self.compose_cmd + [
                    '-f', str(compose_file),
                    'exec', '-T', 'kafka',
                    'kafka-topics', '--bootstrap-server', 'localhost:9092',
                    '--list'
                ]
                result = subprocess.run(
                    cmd_check,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Check if topic already exists
                if result.returncode == 0 and topic_name in result.stdout:
                    print_info(f"Topic '{topic_name}' already exists")
                    continue
                
                # Create topic
                cmd_create = self.compose_cmd + [
                    '-f', str(compose_file),
                    'exec', '-T', 'kafka',
                    'kafka-topics', '--bootstrap-server', 'localhost:9092',
                    '--create',
                    '--topic', topic_name,
                    '--partitions', str(partitions),
                    '--replication-factor', '1',
                    '--if-not-exists'
                ]
                
                result = subprocess.run(
                    cmd_create,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    print_success(f"Topic '{topic_name}' created successfully")
                else:
                    # Topic might already exist, check error message
                    if 'already exists' in result.stderr.lower() or 'already exists' in result.stdout.lower():
                        print_info(f"Topic '{topic_name}' already exists")
                    else:
                        print_warning(f"Could not create topic '{topic_name}': {result.stderr}")
                        
            except subprocess.TimeoutExpired:
                print_warning(f"Timeout creating topic '{topic_name}'")
            except Exception as e:
                print_warning(f"Error creating topic '{topic_name}': {e}")
        
        # Give Kafka a moment to register the topics
        time.sleep(2)
    
    def run_django_migrations(self) -> bool:
        """Run Django database migrations."""
        print_info("Running Django migrations...")
        
        try:
            cmd = [sys.executable, 'manage.py', 'migrate']
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print_success("Django migrations completed")
                return True
            else:
                print_warning(f"Migrations may have issues: {result.stderr}")
                return False
        except Exception as e:
            print_error(f"Error running migrations: {e}")
            return False
    
    def start_django_server(self):
        """Start Django development server."""
        print_info("Starting Django server on http://localhost:8000...")
        
        cmd = [sys.executable, 'manage.py', 'runserver']
        process = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr with stdout
            text=True,
            bufsize=1  # Line buffered
        )
        self.processes.append(process)
        
        # Monitor output in a thread
        def monitor_output():
            try:
                for line in iter(process.stdout.readline, ''):
                    if not self.running:
                        break
                    if line:
                        print(f"{Colors.BLUE}[Django]{Colors.RESET} {line.strip()}")
            except Exception as e:
                if self.running:
                    print_error(f"Django output monitor error: {e}")
        
        thread = threading.Thread(target=monitor_output, daemon=True)
        thread.start()
        self.threads.append(thread)
        
        time.sleep(3)  # Give Django time to start
        if process.poll() is None:
            print_success("Django server started")
        else:
            print_error("Django server failed to start")
    
    def start_fastapi_collector(self):
        """Start FastAPI event collector."""
        print_info("Starting FastAPI event collector on http://localhost:9000...")
        
        collector_dir = self.project_root / 'event_system' / 'collector'
        cmd = [sys.executable, '-m', 'uvicorn', 'main:app', '--reload', '--port', '9000', '--host', '0.0.0.0']
        
        process = subprocess.Popen(
            cmd,
            cwd=collector_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr with stdout
            text=True,
            bufsize=1  # Line buffered
        )
        self.processes.append(process)
        
        # Monitor output in a thread
        def monitor_output():
            try:
                for line in iter(process.stdout.readline, ''):
                    if not self.running:
                        break
                    if line:
                        print(f"{Colors.CYAN}[FastAPI]{Colors.RESET} {line.strip()}")
            except Exception as e:
                if self.running:
                    print_error(f"FastAPI output monitor error: {e}")
        
        thread = threading.Thread(target=monitor_output, daemon=True)
        thread.start()
        self.threads.append(thread)
        
        time.sleep(3)  # Give FastAPI time to start
        if process.poll() is None:
            print_success("FastAPI collector started")
        else:
            print_error("FastAPI collector failed to start")
    
    def start_kafka_consumer(self, script_name: str, display_name: str):
        """Start a Kafka consumer script."""
        print_info(f"Starting {display_name}...")
        
        script_path = self.project_root / script_name
        if not script_path.exists():
            print_error(f"Consumer script not found: {script_path}")
            return
        
        cmd = [sys.executable, str(script_path)]
        process = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr with stdout
            text=True,
            bufsize=1  # Line buffered
        )
        self.processes.append(process)
        
        # Monitor output in a thread
        def monitor_output():
            try:
                for line in iter(process.stdout.readline, ''):
                    if not self.running:
                        break
                    if line:
                        print(f"{Colors.YELLOW}[{display_name}]{Colors.RESET} {line.strip()}")
            except Exception as e:
                if self.running:
                    print_error(f"{display_name} output monitor error: {e}")
        
        thread = threading.Thread(target=monitor_output, daemon=True)
        thread.start()
        self.threads.append(thread)
        
        time.sleep(2)
        if process.poll() is None:
            print_success(f"{display_name} started")
        else:
            # Check if there's an error message
            return_code = process.poll()
            print_error(f"{display_name} failed to start (exit code: {return_code})")
    
    def start_flink_job(self, job_file: str, display_name: str):
        """Start a Flink job inside the Flink container."""
        print_info(f"Starting {display_name} in Flink container...")
        
        compose_file = self.project_root / 'docker-compose.yml'
        job_path = f"/opt/flink/usrlib/{job_file}"
        
        # Check if job file exists
        local_job_path = self.project_root / job_file
        if not local_job_path.exists():
            print_error(f"Flink job file not found: {local_job_path}")
            return
        
        # Set environment variables for Docker network
        # Inside Docker, use service names instead of localhost
        # Determine topic based on job file
        kafka_topic = 'cart_events' if 'cart' in job_file.lower() else 'user_events'
        env_vars = {
            'KAFKA_BOOTSTRAP': 'kafka:9092',
            'KAFKA_TOPIC': kafka_topic,
            'REDIS_HOST': 'redis',
            'REDIS_PORT': '6379',
        }
        
        # First, try to install required Python packages
        print_info("Installing required Python packages in Flink container...")
        install_cmd = self.compose_cmd + [
            '-f', str(compose_file),
            'exec', '-T', 'flink-taskmanager',
            'pip3', 'install', '--quiet', 'redis', 'joblib', 'numpy'
        ]
        
        try:
            install_result = subprocess.run(
                install_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            if install_result.returncode == 0:
                print_success("Python packages installed")
            else:
                print_warning(f"Some packages may not have installed: {install_result.stderr}")
        except Exception as e:
            print_warning(f"Could not install packages: {e}")
        
        # Try to run the job inside the Flink container
        # PyFlink jobs run as Python scripts that connect to the Flink cluster
        env_flags = []
        for key, value in env_vars.items():
            env_flags.extend(['-e', f"{key}={value}"])
        
        cmd = self.compose_cmd + [
            '-f', str(compose_file),
            'exec', '-d'
        ] + env_flags + [
            'flink-taskmanager',
            'python3', job_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print_success(f"{display_name} started in Flink container")
                print_info(f"Check Flink Web UI at http://localhost:8081 to see job status")
                # Give it a moment to start
                time.sleep(3)
            else:
                print_warning(f"Could not start Flink job automatically")
                if result.stderr:
                    print_info(f"Error: {result.stderr}")
                print_info(f"Note: PyFlink jobs may need to be submitted via Flink's job submission API")
                env_str = ' '.join([f"-e {k}={v}" for k, v in env_vars.items()])
                print_info(f"To start manually, run:")
                print_info(f"  docker exec -it {env_str} flink-taskmanager python3 {job_path}")
                
        except Exception as e:
            print_warning(f"Could not start Flink job automatically: {e}")
            env_str = ' '.join([f"-e {k}={v}" for k, v in env_vars.items()])
            print_info(f"To start manually, run:")
            print_info(f"  docker exec -it {env_str} flink-taskmanager python3 {job_path}")
    
    def stop_all(self):
        """Stop all running processes."""
        print_info("Stopping all services...")
        
        # Stop Python processes
        for process in self.processes:
            try:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            except Exception as e:
                print_warning(f"Error stopping process: {e}")
        
        # Stop Docker services
        try:
            compose_file = self.project_root / 'docker-compose.yml'
            cmd = self.compose_cmd + ['-f', str(compose_file), 'down']
            subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                timeout=30
            )
            print_success("Docker services stopped")
        except Exception as e:
            print_warning(f"Error stopping Docker services: {e}")
    
    def start_all(self):
        """Start all services in the correct order."""
        print_info("=" * 60)
        print_info("Starting Churn Prediction System")
        print_info("=" * 60)
        
        # Check prerequisites
        if not self.check_docker():
            return False
        
        if not self.check_docker_compose():
            return False
        
        # Start Docker services
        if not self.start_docker_services():
            return False
        
        # Wait for services to be ready
        self.wait_for_docker_services()
        
        # Create Kafka topics
        self.create_kafka_topics()
        
        # Run migrations
        self.run_django_migrations()
        
        # Start Python services
        print_info("\n" + "=" * 60)
        print_info("Starting Python Services")
        print_info("=" * 60)
        
        self.start_django_server()
        time.sleep(2)
        
        self.start_fastapi_collector()
        time.sleep(2)
        
        self.start_kafka_consumer('consumer.py', 'User Events Consumer')
        time.sleep(2)
        
        self.start_kafka_consumer('cart_consumer.py', 'Cart Events Consumer')
        time.sleep(2)
        
        # Start Flink job
        self.start_flink_job('flink_cart_abandon_job.py', 'Flink Cart Abandon Job')
        
        # Print summary
        print_info("\n" + "=" * 60)
        print_success("All services started successfully!")
        print_info("=" * 60)
        print_info("Services running:")
        print_info("  • Django Server: http://localhost:8000")
        print_info("  • FastAPI Collector: http://localhost:9000")
        print_info("  • Kafka: localhost:9092")
        print_info("  • Redis: localhost:6380")
        print_info("  • PostgreSQL: localhost:5432")
        print_info("  • Flink JobManager: http://localhost:8081")
        print_info("=" * 60)
        print_warning("Press Ctrl+C to stop all services")
        print_info("=" * 60)
        
        # Keep running until interrupted
        dead_processes = set()  # Track which processes have already been reported as dead
        try:
            while self.running:
                time.sleep(5)  # Check less frequently to reduce spam
                # Check if any process has died
                for i, process in enumerate(self.processes):
                    if i not in dead_processes and process.poll() is not None:
                        return_code = process.poll()
                        service_names = ['Django', 'FastAPI', 'User Events Consumer', 'Cart Events Consumer']
                        service_name = service_names[i] if i < len(service_names) else f"Service {i}"
                        print_error(f"{service_name} has stopped unexpectedly (exit code: {return_code})")
                        dead_processes.add(i)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_all()


def main():
    """Main entry point."""
    # Get project root directory
    project_root = Path(__file__).resolve().parent
    
    # Change to project root
    os.chdir(project_root)
    
    # Create and start service manager
    manager = ServiceManager(project_root)
    manager.start_all()


if __name__ == '__main__':
    main()

