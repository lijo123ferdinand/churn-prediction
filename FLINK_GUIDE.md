# Flink Processing Jobs Guide

This guide explains how to use Flink processing jobs in the churn prediction system.

## Overview

Flink jobs provide real-time stream processing capabilities for:
- **Churn Prediction**: Real-time churn score computation using ML models
- **Cart Abandonment**: Real-time cart abandonment detection and alerts

## Two Execution Modes

### 1. Local Execution (PyFlink) - Default

Flink jobs run as Python processes using PyFlink in local execution mode. This is simpler and doesn't require a Flink cluster.

**Start jobs:**
```bash
python scripts/start_flink_jobs.py
```

**Stop jobs:**
```bash
python scripts/stop_flink_jobs.py
```

### 2. Flink Cluster Execution

For production or distributed processing, use the Flink cluster in Docker.

**Start Flink cluster:**
```bash
docker-compose up -d flink-jobmanager flink-taskmanager
```

**Access Flink Web UI:**
- URL: http://localhost:8081
- Monitor jobs, check metrics, view logs

**Submit jobs to cluster:**
```bash
# Submit churn prediction job
flink run -py streaming/processors/flink_churn_ml_processor.py

# Submit cart abandonment job
flink run -py streaming/processors/flink_cart_processor.py
```

## Available Flink Jobs

### 1. Churn Prediction ML Processor
- **File**: `streaming/processors/flink_churn_ml_processor.py`
- **Function**: Real-time churn score prediction using ML model
- **Input**: Kafka topic `user_events`
- **Output**: Churn scores stored in Redis

**Features:**
- Loads ML model from `ml/models/churn_model.pkl` or `.joblib`
- Computes features from event stream
- Updates Redis with real-time churn scores

### 2. Cart Abandonment Processor
- **File**: `streaming/processors/flink_cart_processor.py`
- **Function**: Real-time cart abandonment detection
- **Input**: Kafka topic `user_events`
- **Output**: Abandonment scores and alerts in Redis

**Features:**
- Stateful processing (tracks cart sessions)
- Timer-based abandonment detection
- Email alerts for high-risk users
- Uses ML model for probability prediction

### 3. Basic Churn Processor (Optional)
- **File**: `streaming/processors/flink_churn_processor.py`
- **Function**: Simple rule-based churn scoring
- **Note**: Less accurate than ML-based version

## Configuration

### Environment Variables

Set in `.env` file:

```bash
# Enable/disable Flink jobs on startup
START_FLINK_JOBS=true

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=user_events

# Redis configuration
REDIS_HOST=localhost
REDIS_PORT=6380

# Model paths
CHURN_MODEL_PATH=ml/models/churn_model.pkl
CART_MODEL_PATH=ml/models/shared_models/cart_model.joblib

# Cart abandonment settings
CART_ABANDON_THRESHOLD=0.75
ABANDON_WINDOW_MIN=60
```

### Kafka Broker Address

**Important**: Flink processors need to connect to Kafka. Update the broker address:

- **Local execution**: Use `localhost:9092`
- **Docker network**: Use `kafka:9092` (if Flink runs in Docker)
- **Custom**: Set `KAFKA_BOOTSTRAP_SERVERS` environment variable

Update in processor files:
```python
# Change from hardcoded:
.set_bootstrap_servers("172.18.0.4:9092")

# To environment variable:
.set_bootstrap_servers(os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
```

## Running Flink Jobs

### Automatic (via Startup Scripts)

Flink jobs are automatically started when you run:
```bash
./scripts/start_all.sh
# or
python scripts/start_all.py
```

Set `START_FLINK_JOBS=false` to disable.

### Manual Start

**Start all jobs:**
```bash
python scripts/start_flink_jobs.py
```

**Start individual job:**
```bash
python streaming/processors/flink_churn_ml_processor.py
python streaming/processors/flink_cart_processor.py
```

### Stop Jobs

**Stop all jobs:**
```bash
python scripts/stop_flink_jobs.py
```

**Stop manually:**
```bash
# Find and kill processes
ps aux | grep flink
kill <PID>
```

## Monitoring

### Logs

Flink job logs are in `logs/` directory:
- `logs/flink_churn_ml.log`
- `logs/flink_cart_abandon.log`

### Flink Web UI

If using Flink cluster:
- Access: http://localhost:8081
- View running jobs
- Check job metrics
- View task manager status

### Redis Monitoring

Check real-time scores in Redis:
```bash
redis-cli -p 6380
> KEYS user:*
> HGETALL user:123
```

## Troubleshooting

### Issue: Flink job can't connect to Kafka

**Solution:**
1. Verify Kafka is running: `docker-compose ps kafka`
2. Check Kafka broker address in processor code
3. Ensure Kafka is accessible from Flink (network configuration)

### Issue: Model file not found

**Solution:**
```bash
# Train models first
python ml/training/train_churn.py
python ml/training/train_cart.py

# Verify model files exist
ls -la ml/models/
```

### Issue: Flink job crashes

**Check logs:**
```bash
tail -f logs/flink_*.log
```

**Common causes:**
- Missing dependencies (install PyFlink: `pip install apache-flink`)
- Model file path incorrect
- Redis/Kafka connection issues

### Issue: PyFlink not installed

**Solution:**
```bash
pip install apache-flink
# Or add to requirements.txt
```

## Performance Tuning

### Parallelism

Adjust parallelism in processor code:
```python
env.set_parallelism(2)  # Increase for more throughput
```

### State Backend

For production, configure state backend:
```python
from pyflink.datastream.state import StateBackend

# Use RocksDB for large state
env.set_state_backend(RocksDBStateBackend("file:///tmp/flink-state"))
```

### Checkpointing

Enable checkpointing for fault tolerance:
```python
env.enable_checkpointing(60000)  # Every 60 seconds
```

## Best Practices

1. **Use Flink cluster for production**: Local execution is fine for development
2. **Monitor job metrics**: Use Flink Web UI to track performance
3. **Set appropriate parallelism**: Balance throughput and resource usage
4. **Enable checkpointing**: For fault tolerance in production
5. **Separate concerns**: Different jobs for different processing needs
6. **Test locally first**: Use local execution before deploying to cluster

## Next Steps

- Review job code in `streaming/processors/`
- Customize processing logic for your use case
- Add more Flink jobs as needed
- Configure production deployment

