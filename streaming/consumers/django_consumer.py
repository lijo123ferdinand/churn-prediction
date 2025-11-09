import os
import django
import json
from datetime import datetime
from django.utils import timezone
from confluent_kafka import Consumer, KafkaException
import threading
from ml.training.train_churn import train_churn_model

# --- Django setup ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'churn_prediction.settings')
django.setup()

from analytics.models import UserEvent
from users.models import User

# --- Kafka setup ---
conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'event-consumer-group',
    'auto.offset.reset': 'earliest',
}

consumer = Consumer(conf)
consumer.subscribe(['user_events'])

# --- Training interval ---
TRAIN_INTERVAL = 3
event_counter = 0
training_in_progress = False


def trigger_training():
    """Run model training in a background thread."""
    global training_in_progress
    if training_in_progress:
        print("⚙️ Training already in progress, skipping.")
        return

    def train():
        global training_in_progress
        training_in_progress = True
        try:
            train_churn_model()
        except Exception as e:
            print(f"❌ Training failed: {e}")
        training_in_progress = False

    threading.Thread(target=train, daemon=True).start()


print("✅ Kafka consumer connected. Listening for events...")

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())

        # Parse the Kafka message
        try:
            event_data = json.loads(msg.value().decode('utf-8'))
        except json.JSONDecodeError:
            print("⚠️ Received invalid JSON — skipping message.")
            continue

        user_id = event_data.get('user_id')
        event_name = event_data.get('event_name', 'unknown')
        properties = event_data.get('properties', {})

        # --- Fix: make timestamp timezone-aware ---
        timestamp_str = event_data.get('timestamp')
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            timestamp = timezone.make_aware(timestamp)
        except Exception:
            timestamp = timezone.now()

        # --- Fix: create user if missing ---
        user, created = User.objects.get_or_create(
            id=user_id,
            defaults={
                "email": f"user_{user_id}@example.com",
                "signup_date": timezone.now(),
                "last_login": timezone.now(),
                "total_spent": 0,
                "total_orders": 0,
            },
        )
        if created:
            print(f"🆕 Created new user with ID {user_id}")

        # --- Update user attributes based on event type ---
        if event_name == "purchase":
            amount = float(properties.get("amount", 0))
            user.total_orders += 1
            user.total_spent += amount

        elif event_name == "login":
            user.last_login = timezone.now()

        user.save()

        # --- Save event to DB ---
        UserEvent.objects.create(
            user_id=user_id,
            event_name=event_name,
            properties=properties,
            timestamp=timestamp,
        )

        event_counter += 1
        print(f"💾 Event #{event_counter} saved: {event_name}")

        # --- Trigger retraining every TRAIN_INTERVAL events ---
        if event_counter % TRAIN_INTERVAL == 0:
            print(f"🎯 {TRAIN_INTERVAL} new events processed — starting retraining...")
            trigger_training()

except KeyboardInterrupt:
    print("🛑 Consumer stopped by user.")
finally:
    consumer.close()
