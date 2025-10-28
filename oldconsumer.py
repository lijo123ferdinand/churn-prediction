import os
import django
import json
from confluent_kafka import Consumer, KafkaException

# --- Setup Django environment ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'churn_prediction.settings')
django.setup()

from analytics.models import UserEvent

# --- Kafka setup ---
conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'event-consumer-group',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(conf)
consumer.subscribe(['user_events'])

print("✅ Kafka consumer connected. Listening for events...")

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())

        event_data = json.loads(msg.value().decode('utf-8'))

        # Save to database
        UserEvent.objects.create(
            user_id=event_data.get('user_id', ''),
            event_name=event_data.get('event_name', ''),
            properties=event_data.get('properties', {}),
            timestamp=event_data.get('timestamp')
        )

        print(f"💾 Event saved: {event_data}")

except KeyboardInterrupt:
    pass
finally:
    consumer.close()
