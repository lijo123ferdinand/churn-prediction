# Directory Restructuring Summary

This document summarizes the restructuring changes made to organize the churn prediction project.

## ✅ Changes Made

### 1. Created New Directory Structure

- **`ml/`** - Machine Learning components
  - `models/` - Trained model files (.pkl, .joblib)
  - `training/` - Training scripts
  - `prediction/` - Prediction scripts

- **`streaming/`** - Event streaming and processing
  - `collectors/` - Event collection services
  - `consumers/` - Kafka consumers
  - `processors/` - Stream processors (Flink jobs)

- **`config/`** - Configuration files
  - `env.example` - Environment variables template

- **`scripts/`** - Utility scripts
- **`archive/`** - Old/unused files

### 2. Files Moved

#### ML Components
- `analytics/train_model.py` → `ml/training/train_churn.py`
- `analytics/train_cart_model.py` → `ml/training/train_cart.py`
- `analytics/predict_churn.py` → `ml/prediction/predict_churn.py`
- `analytics/predict_cart_abandon.py` → `ml/prediction/predict_cart_abandon.py`
- `churn_model.pkl` → `ml/models/churn_model.pkl`
- `app/churn_model.joblib` → `ml/models/churn_model.joblib`

#### Streaming Components
- `consumer.py` → `streaming/consumers/django_consumer.py`
- `event_system/collector/main.py` → `streaming/collectors/fastapi_collector.py`
- `kafka_redis_processor.py` → `streaming/processors/flink_churn_processor.py`
- `kafka_redis_processor_ml.py` → `streaming/processors/flink_churn_ml_processor.py`
- `flink_cart_abandon_job.py` → `streaming/processors/flink_cart_processor.py`

#### Utilities
- `analytics/generate_fake_users.py` → `scripts/generate_fake_users.py`

#### Archived
- `analytics/old*.py` → `archive/`
- `oldconsumer.py` → `archive/`

### 3. Updated Imports and Paths

All moved files have been updated with:
- Correct `BASE_DIR` calculations for new locations
- Updated model paths to `ml/models/`
- Fixed import statements to reflect new structure
- Updated Flink processors to use new model paths

### 4. Fixed Issues

- ✅ Removed duplicate `path` import in `churn_prediction/urls.py`
- ✅ Standardized model file paths
- ✅ Created proper Python package structure with `__init__.py` files
- ✅ Created environment variable template

### 5. Documentation Created

- `README.md` - Main project documentation
- `PROJECT_STRUCTURE.md` - Detailed directory layout
- `RESTRUCTURING_SUMMARY.md` - This file
- `config/env.example` - Environment variables template

## 📋 Migration Checklist

If you're migrating from the old structure:

- [ ] Update any external scripts that reference old paths
- [ ] Update CI/CD pipelines if they reference specific file paths
- [ ] Update documentation that references old file locations
- [ ] Test all training and prediction scripts
- [ ] Verify Kafka consumers and processors work correctly
- [ ] Check that model files are accessible from new locations

## 🔄 Backward Compatibility

Some files still reference the old structure through Django apps:
- `analytics/utils.py` - Still in `analytics/` (Django app)
- `analytics/utils_cart.py` - Still in `analytics/` (Django app)
- `analytics/models.py` - Still in `analytics/` (Django app)
- `analytics/views.py` - Still in `analytics/` (Django app)

These remain in place as they are Django app components.

## 🎯 Benefits

1. **Clear Separation of Concerns**: ML, streaming, and Django code are separated
2. **Better Organization**: Related files are grouped together
3. **Easier Maintenance**: Finding and updating code is simpler
4. **Scalability**: Structure supports future growth
5. **Professional Structure**: Follows industry best practices

## ⚠️ Important Notes

- Model files are now in `ml/models/` - ensure backups are updated
- Flink jobs need to be updated if they reference model paths
- Environment variables should be set using the new `config/env.example` template
- Old files are in `archive/` and can be removed after verification

