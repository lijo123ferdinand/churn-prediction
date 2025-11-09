# 🚀 Quick Start Guide

The fastest way to get the Churn Prediction System running.

## Option 1: Automated Scripts (Recommended)

### Linux/macOS

```bash
# Start everything
./scripts/start_all.sh

# Stop everything
./scripts/stop_all.sh
```

### Windows (PowerShell)

```powershell
# Start everything
.\scripts\start_all.ps1

# Stop - Close terminal or use Task Manager
```

### Python (Cross-platform)

```bash
# Start everything
python scripts/start_all.py

# Stop (Ctrl+C or in another terminal)
python scripts/stop_all.py
```

---

## Option 2: Manual Start (3 Terminals)

### Terminal 1: Infrastructure

```bash
docker-compose up -d
```

### Terminal 2: Django

```bash
python manage.py migrate
python manage.py runserver
```

### Terminal 3: Services

```bash
# FastAPI Collector
cd streaming/collectors
uvicorn fastapi_collector:app --reload --port 9000

# In another terminal: Kafka Consumer
python streaming/consumers/django_consumer.py
```

---

## ✅ Verify It's Working

1. **Check Django**: http://localhost:8000/analytics/churn-dashboard/
2. **Check Admin Panel**: http://localhost:8000/admin/
   - Default login: `admin` / `admin123` (⚠️ change after first login!)
3. **Check Collector**: http://localhost:9000/
4. **Send Test Event**:
   ```bash
   curl -X POST http://localhost:9000/collect \
     -H "Content-Type: application/json" \
     -d '{"user_id": 123, "event_name": "login", "timestamp": "2024-01-10T10:00:00Z"}'
   ```

---

## 📚 More Details

See [HOW_TO_RUN.md](HOW_TO_RUN.md) for complete documentation.
