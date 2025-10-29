(venv) PS C:\Users\lijo_ferdinand\Desktop\projects\churn_prediction> python manage.py runserver
(venv) PS C:\Users\lijo_ferdinand\Desktop\projects\churn_prediction\event_system\collector> uvicorn main:app --reload --port 9000
or 
uvicorn main:app --reload --host 0.0.0.0 --port 9000

(venv) PS C:\Users\lijo_ferdinand\Desktop\projects\churn_prediction\event_system> python consumer.py
(venv) PS C:\Users\lijo_ferdinand\Desktop\projects\churn_prediction> python consumer.py
(if needed)
python manage.py makemigrations
python manage.py migrate

sudo yum install python3.10  # or python3.8 depending on repo
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt








_____________________________________________


docker run -d \
  --name postgres-db \
  -e POSTGRES_DB=churn_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:16


python manage.py shell

from analytics.models import UserEvent
from users.models import User

UserEvent.objects.all().delete()
User.objects.all().delete()



docker exec -it opt-kafka-1 bash
kafka-topics --bootstrap-server localhost:9092 --list
kafka-topics --bootstrap-server localhost:9092 \
  --create \
  --topic user_events \
  --partitions 3 \
  --replication-factor 1





_________________________________________________________




version: "3.8"

services:
  # ---- Zookeeper ----
  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.1
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"

  # ---- Kafka ----
  kafka:
    image: confluentinc/cp-kafka:7.6.1
    depends_on:
      - zookeeper
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_LISTENERS: PLAINTEXT://:9092
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    ports:
      - "9092:9092"

  flink-jobmanager:
    build: .
    hostname: flink-jobmanager
    container_name: opt-flink-jobmanager-1
    command: jobmanager
    environment:
      - JOB_MANAGER_RPC_ADDRESS=flink-jobmanager
    ports:
      - "8081:8081"
    volumes:
      - ./flink:/opt/flink
    depends_on:
      - kafka
      - redis

  flink-taskmanager:
    build: .
    hostname: flink-taskmanager
    container_name: opt-flink-taskmanager-1
    command: taskmanager
    environment:
      - JOB_MANAGER_RPC_ADDRESS=flink-jobmanager
    volumes:
      - ./flink:/opt/flink
    depends_on:
      - flink-jobmanager
  # ---- Redis ----
  redis:
    image: redis:latest
    ports:
      - "6380:6379"





_____________________________________________


{
  "user_id": 504,
  "event_name": "signup",
  "properties": {
    "source": "referral"
  },
  "timestamp": "2024-01-10T10:00:00Z"
}

