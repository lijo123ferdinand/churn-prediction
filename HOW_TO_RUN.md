# How to Run the Churn Prediction System

This guide explains how to start all components of the system.

## 🚀 Quick Start (Automated)

### Linux/macOS

```bash
chmod +x scripts/start_all.sh
./scripts/start_all.sh
```

### Windows (PowerShell)

```powershell
.\scripts\start_all.ps1
```

### Stop All Services

```bash
# Linux/macOS
./scripts/stop_all.sh

# Windows - Close terminal or use Task Manager
```

---

## 📋 Manual Setup (Step by Step)

### Prerequisites

1. **Python 3.10+** with virtual environment
2. **Docker & Docker Compose** for Kafka, Redis, Zookeeper
3. **PostgreSQL** database (or use Docker)

### Step 1: Setup Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp config/env.example .env
# Edit .env with your configuration
```

### Step 2: Start Infrastructure Services

```bash
# Start Kafka, Redis, Zookeeper via Docker
docker-compose up -d

# Verify services are running
docker-compose ps

# Check Kafka topics (optional)
docker exec -it opt-kafka-1 bash
kafka-topics --bootstrap-server localhost:9092 --list
```

**Expected Services:**

- Zookeeper: `localhost:2181`
- Kafka: `localhost:9092`
- Redis: `localhost:6380`
- PostgreSQL: `localhost:5432`
- Flink JobManager: `localhost:8081` (Web UI)
- Flink TaskManager: Running (no external port)

### Step 3: Setup Database

```bash
# Run migrations
python manage.py migrate

# Create superuser (automatically done by startup scripts)
# Or manually:
python scripts/create_superuser.py
# Or use Django's interactive command:
python manage.py createsuperuser
```

**Note:** The startup scripts automatically check and create a superuser if none exists. Default credentials:

- Username: `admin`
- Email: `admin@example.com`
- Password: `admin123`

⚠️ **Change the default password after first login!**

You can customize these in your `.env` file:

```bash
DJANGO_SUPERUSER_USERNAME=your_username
DJANGO_SUPERUSER_EMAIL=your_email@example.com
DJANGO_SUPERUSER_PASSWORD=your_secure_password
```

### Step 4: Start Application Services

You need to run these in **separate terminal windows/tabs**:

#### Terminal 1: Django Server

```bash
python manage.py runserver
```

**Access:** http://localhost:8000

- Dashboard: http://localhost:8000/analytics/churn-dashboard/
- Admin: http://localhost:8000/admin/

#### Terminal 2: FastAPI Event Collector

```bash
cd streaming/collectors
uvicorn fastapi_collector:app --reload --host 0.0.0.0 --port 9000
```

**Access:** http://localhost:9000

- Health check: http://localhost:9000/
- Test: http://localhost:9000/test

#### Terminal 3: Kafka Consumer

```bash
python streaming/consumers/django_consumer.py
```

This processes events from Kafka and triggers model retraining.

#### Terminal 4: Flink Jobs (Optional)

```bash
# Start all Flink jobs
python scripts/start_flink_jobs.py

# Or start individual jobs:
python streaming/processors/flink_churn_ml_processor.py
python streaming/processors/flink_cart_processor.py
```

**Note:** Flink jobs are automatically started by the startup scripts if `START_FLINK_JOBS=true` (default).

---

## 🧪 Testing the System

### 1. Send Test Event to Collector

```bash
curl -X POST http://localhost:9000/collect \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123,
    "event_name": "login",
    "properties": {"source": "web"},
    "timestamp": "2024-01-10T10:00:00Z"
  }'
```

### 2. Check Django Consumer

The consumer should log:

```
💾 Event #1 saved: login
```

### 3. View Dashboard

Open http://localhost:8000/analytics/churn-dashboard/ to see user churn scores.

### 4. Check Redis

```bash
redis-cli -p 6380
> KEYS user:*
> HGETALL user:123
```

---

## 🔧 Training Models

### Train Churn Model

```bash
python ml/training/train_churn.py
```

### Train Cart Abandonment Model

```bash
python ml/training/train_cart.py
```

### Run Predictions

```bash
# Churn prediction
python ml/prediction/predict_churn.py

# Cart abandonment prediction
python ml/prediction/predict_cart_abandon.py
```

---

## 📊 Service Ports

| Service           | Port | URL                   |
| ----------------- | ---- | --------------------- |
| Django            | 8000 | http://localhost:8000 |
| FastAPI Collector | 9000 | http://localhost:9000 |
| Kafka             | 9092 | localhost:9092        |
| Redis             | 6380 | localhost:6380        |
| PostgreSQL        | 5432 | localhost:5432        |
| Flink Web UI      | 8081 | http://localhost:8081 |
| Zookeeper         | 2181 | localhost:2181        |

---

## 🐛 Troubleshooting

### Issue: Port already in use

```bash
# Find process using port
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process or change port in settings
```

### Issue: Kafka not connecting

```bash
# Check if Kafka is running
docker-compose ps

# Check Kafka logs
docker-compose logs kafka

# Verify Kafka is accessible
docker exec -it opt-kafka-1 bash
kafka-topics --bootstrap-server localhost:9092 --list
```

### Issue: Redis connection failed

```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
redis-cli -p 6380 ping
# Should return: PONG
```

### Issue: Database connection failed

```bash
# Check PostgreSQL is running
docker-compose ps postgres-db

# Check PostgreSQL logs
docker-compose logs postgres-db

# Verify database exists
docker exec -it postgres-db psql -U postgres -l
```

- Verify credentials in `.env` or `settings.py` match docker-compose.yml
- Database `churn_db` is created automatically by docker-compose

### Issue: Model file not found

```bash
# Train models first
python ml/training/train_churn.py
python ml/training/train_cart.py

# Verify model files exist
ls -la ml/models/
```

---

## 🔄 Development Workflow

1. **Start infrastructure:** `docker-compose up -d`
2. **Start Django:** `python manage.py runserver`
3. **Start collector:** `uvicorn fastapi_collector:app --reload --port 9000`
4. **Start consumer:** `python streaming/consumers/django_consumer.py`
5. **Send test events** via curl or frontend
6. **Monitor logs** in each terminal
7. **Check dashboard** for results

---

## 📝 Notes

- **Logs:** Check terminal output for each service
- **Background mode:** Use `&` on Linux/macOS or `Start-Process` on Windows
- **Auto-restart:** Use `--reload` flag with uvicorn for development
- **Production:** Use process managers like `systemd`, `supervisord`, or `pm2`

---

## 🎯 Next Steps

After starting all services:

1. Send test events to the collector
2. Monitor the consumer processing events
3. Check the dashboard for churn scores
4. Train models with real data
5. Set up scheduled prediction jobs

For more details, see [README.md](README.md) and [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md).
