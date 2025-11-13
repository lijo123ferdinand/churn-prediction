import os
import django
import json
import threading
from datetime import datetime
from django.utils import timezone
from confluent_kafka import Consumer, KafkaException

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'churn_prediction.settings')
django.setup()

from analytics.models import CartEvent
from users.models import User
from analytics.train_cart_model import train_cart_model
from analytics.predict_cart_abandon import predict_cart_abandon

KAFKA_TOPIC = "cart_events"

# Kafka config
conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'cart-abandon-consumer-group',
    'auto.offset.reset': 'earliest',
}

consumer = Consumer(conf)
consumer.subscribe([KAFKA_TOPIC])

TRAIN_INTERVAL = 5
event_counter = 0
training_in_progress = False


def trigger_training():
    """Run cart model training + prediction in background."""
    global training_in_progress
    if training_in_progress:
        print("⚙️ Training already running — skipping.")
        return

    def job():
        global training_in_progress
        training_in_progress = True
        try:
            train_cart_model()
            predict_cart_abandon()
        except Exception as e:
            print(f"❌ Training failed: {e}")
        training_in_progress = False

    threading.Thread(target=job, daemon=True).start()


print(f"🛒 Cart Consumer started. Listening on topic: {KAFKA_TOPIC}")

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())

        try:
            event = json.loads(msg.value().decode("utf-8"))
        except json.JSONDecodeError:
            print("⚠️ Invalid JSON — skipped.")
            continue

        user_id = event.get("user_id")
        event_name = event.get("event_name", "unknown")
        properties = event.get("properties", {})

        # Timestamp
        ts_raw = event.get("timestamp")
        try:
            timestamp = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            timestamp = timezone.make_aware(timestamp)
        except Exception:
            timestamp = timezone.now()

        # Ensure user exists
        user, created = User.objects.get_or_create(
            id=user_id,
            defaults={
                "email": f"user_{user_id}@example.com",
                "signup_date": timezone.now(),
                "last_login": timezone.now(),
            },
        )
        if created:
            print(f"🆕 Created User {user_id}")

        # ---------------------------
        # Update USER CART METRICS
        # ---------------------------

        user.cart_events = getattr(user, "cart_events", 0)
        user.items_added = getattr(user, "items_added", 0)
        user.cart_value_sum = getattr(user, "cart_value_sum", 0)
        user.had_checkout = getattr(user, "had_checkout", False)

        if event_name == "add_to_cart":
            user.items_added += 1
            user.cart_events += 1
            price = float(properties.get("price", 0))
            user.cart_value_sum += price

        elif event_name == "remove_from_cart":
            user.cart_events += 1

        elif event_name == "checkout":
            user.had_checkout = True
            user.cart_events += 1

        elif event_name == "update_quantity":
            user.cart_events += 1

        user.save()

        # Save raw cart event
        CartEvent.objects.create(
            user=user,
            event_name=event_name,
            properties=properties,
            timestamp=timestamp,
        )

        event_counter += 1
        print(f"💾 Cart Event #{event_counter} saved: {event_name}")

        if event_counter % TRAIN_INTERVAL == 0:
            print("🎯 Training cart model now...")
            trigger_training()

except KeyboardInterrupt:
    print("🛑 Cart consumer stopped.")

finally:
    consumer.close()
