# Project Structure

This document describes the organized structure of the Churn Prediction System.

## Directory Layout

```
churn-prediction/
├── config/                      # Configuration files
│   ├── .env.example            # Environment variables template
│   └── settings/               # Django settings overrides
│
├── ml/                          # Machine Learning components
│   ├── models/                 # Trained model files (.pkl, .joblib)
│   │   ├── churn_model.pkl
│   │   └── cart_model.joblib
│   ├── training/               # Model training scripts
│   │   ├── train_churn.py
│   │   └── train_cart.py
│   └── prediction/             # Prediction scripts
│       ├── predict_churn.py
│       └── predict_cart_abandon.py
│
├── streaming/                   # Event streaming and processing
│   ├── collectors/             # Event collection services
│   │   └── fastapi_collector.py
│   ├── consumers/              # Kafka consumers
│   │   ├── event_consumer.py
│   │   └── django_consumer.py
│   └── processors/             # Stream processors (Flink)
│       ├── flink_churn_processor.py
│       └── flink_cart_processor.py
│
├── churn_prediction/            # Django project root
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/                        # Django applications
│   ├── users/                  # User management app
│   │   ├── models.py
│   │   ├── views.py
│   │   └── admin.py
│   └── analytics/              # Analytics and ML integration
│       ├── models.py
│       ├── views.py
│       ├── urls.py
│       ├── utils.py
│       └── templates/
│
├── event_system/                # Event SDK and utilities
│   ├── sdk/
│   │   ├── python/
│   │   └── js/
│   └── collector/              # Legacy collector (to be migrated)
│
├── scripts/                     # Utility scripts
│   ├── generate_fake_users.py
│   └── setup_db.py
│
├── docker-compose.yml           # Docker services configuration
├── requirements.txt             # Python dependencies
├── manage.py                    # Django management script
└── README.md                    # Project documentation
```

## Component Descriptions

### ML Module (`ml/`)
- **models/**: Stores trained model files
- **training/**: Scripts for training and retraining models
- **prediction/**: Scripts for batch prediction jobs

### Streaming Module (`streaming/`)
- **collectors/**: Services that collect events from external sources
- **consumers/**: Kafka consumers that process events
- **processors/**: Real-time stream processing (Flink jobs)

### Django Apps (`apps/`)
- **users/**: User model and management
- **analytics/**: Analytics dashboard, API endpoints, and ML integration

### Configuration (`config/`)
- Environment variables and settings
- Separate from code for security

## Migration Notes

Files have been reorganized from the old structure:
- `analytics/train_model.py` → `ml/training/train_churn.py`
- `analytics/predict_churn.py` → `ml/prediction/predict_churn.py`
- `consumer.py` → `streaming/consumers/django_consumer.py`
- `event_system/collector/main.py` → `streaming/collectors/fastapi_collector.py`
- Model files consolidated in `ml/models/`

