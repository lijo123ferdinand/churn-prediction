# Churn Prediction System

A real-time churn prediction and cart abandonment detection system built with Django, Kafka, Redis, and machine learning.

## 📁 Project Structure

```
churn-prediction/
├── config/                  # Configuration files
│   └── env.example         # Environment variables template
├── ml/                     # Machine Learning components
│   ├── models/            # Trained model files
│   ├── training/          # Model training scripts
│   └── prediction/        # Prediction scripts
├── streaming/              # Event streaming and processing
│   ├── collectors/        # Event collection services
│   ├── consumers/         # Kafka consumers
│   └── processors/        # Stream processors (Flink)
├── churn_prediction/       # Django project root
├── apps/                   # Django applications
│   ├── users/            # User management
│   └── analytics/        # Analytics and ML integration
├── event_system/           # Event SDK and utilities
├── scripts/                # Utility scripts
└── archive/               # Old/unused files
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed documentation.

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL
- Redis
- Kafka (via Docker Compose)

### Installation

1. **Clone and setup virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp config/env.example .env
   # Edit .env with your configuration
   ```

3. **Setup database:**
   ```bash
   python manage.py migrate
   ```

4. **Start services (Docker Compose):**
   ```bash
   docker-compose up -d
   ```

5. **Start Django server:**
   ```bash
   python manage.py runserver
   ```

6. **Start event collector (FastAPI):**
   ```bash
   cd streaming/collectors
   uvicorn fastapi_collector:app --reload --port 9000
   ```

7. **Start Kafka consumer:**
   ```bash
   python streaming/consumers/django_consumer.py
   ```

## 📊 Components

### Machine Learning Models

- **Churn Prediction**: Predicts user churn probability
  - Train: `python ml/training/train_churn.py`
  - Predict: `python ml/prediction/predict_churn.py`

- **Cart Abandonment**: Detects cart abandonment risk
  - Train: `python ml/training/train_cart.py`
  - Predict: `python ml/prediction/predict_cart_abandon.py`

### Event Processing

- **Collector**: FastAPI service that receives events and publishes to Kafka
- **Consumer**: Django-based Kafka consumer that processes events and triggers model retraining
- **Processors**: Flink jobs for real-time stream processing

### Django Apps

- **Users**: User model with churn scores
- **Analytics**: Dashboard and API endpoints for churn scores

## 🔧 Configuration

Key configuration options in `.env`:

- Database: PostgreSQL connection settings
- Redis: Host and port for real-time data
- Kafka: Bootstrap servers and topics
- Email: AWS SES credentials for alerts
- Models: Paths to trained model files

## 📡 API Endpoints

- `GET /analytics/churn-dashboard/` - HTML dashboard
- `GET /analytics/api/churn/<user_id>/` - JSON churn score API
- `POST /collect` - Event collection endpoint (FastAPI)

## 🐳 Docker Services

The `docker-compose.yml` includes:
- Zookeeper
- Kafka
- Redis

## 📝 Notes

- Models are stored in `ml/models/`
- Old/unused files are in `archive/`
- Event processing uses incremental learning for continuous model updates
- Real-time scores are stored in Redis for fast dashboard access

## 🔒 Security

⚠️ **Important**: Never commit `.env` files or sensitive credentials. Use `config/env.example` as a template.

## 📚 Documentation

- [Project Structure](PROJECT_STRUCTURE.md) - Detailed directory layout
- [README.txt](readme.txt) - Original setup instructions

