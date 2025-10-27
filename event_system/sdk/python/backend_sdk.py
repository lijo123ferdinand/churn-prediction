from confluent_kafka import Producer
import json, time

class BackendAnalytics:
    def __init__(self, servers="localhost:9092", topic="user_events"):
        self.producer = Producer({'bootstrap.servers': servers})
        self.topic = topic

    def track(self, event, user_id, properties=None, source="backend"):
        msg = {
            "event": event,
            "user_id": user_id,
            "properties": properties or {},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": source,
        }
        self.producer.produce(self.topic, json.dumps(msg).encode('utf-8'))
        self.producer.flush()