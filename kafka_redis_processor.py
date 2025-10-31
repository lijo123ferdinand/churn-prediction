import json
import redis
from datetime import datetime

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer
from pyflink.common.typeinfo import Types
from pyflink.common.watermark_strategy import WatermarkStrategy
from pyflink.common.serialization import SimpleStringSchema


# --- Redis Setup ---
redis_client = redis.Redis(host="localhost", port=6380, db=0)


def parse_event(raw):
    try:
        event = json.loads(raw)
        return event
    except Exception as e:
        print(f"Invalid JSON: {raw}, error: {e}")
        return None


def compute_features(event):
    from datetime import datetime
    import json

    if not event or "user_id" not in event:
        return None

    # Create Redis client inside the function
    r = redis.Redis(host="localhost", port=6380, db=0)

    user_id = event["user_id"]
    event_name = event.get("event_name")
    timestamp_str = event.get("timestamp")
    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

    user_key = f"user:{user_id}"
    existing = r.hgetall(user_key)

    event_count = int(existing.get(b"event_count", 0))
    last_event_time = (
        datetime.fromisoformat(existing[b"last_event_time"].decode())
        if b"last_event_time" in existing
        else None
    )

    event_count += 1
    time_diff = (
        (timestamp - last_event_time).total_seconds() / 3600 if last_event_time else 0
    )
    churn_score = max(0.0, min(1.0, 1 - (event_count / 10) + (time_diff / 24)))

    r.hset(
        user_key,
        mapping={
            "user_id": user_id,
            "event_count": event_count,
            "last_event_time": timestamp.isoformat(),
            "churn_score": churn_score,
        },
    )

    return json.dumps(
        {
            "user_id": user_id,
            "event_count": event_count,
            "churn_score": churn_score,
            "event_name": event_name,
            "timestamp": timestamp_str,
        }
    )

def main():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)

    # --- Kafka Source ---
    source = (
        KafkaSource.builder()
        .set_bootstrap_servers("172.18.0.4:9092")
        .set_topics("user_events")
        .set_group_id("flink_churn")
        .set_starting_offsets(KafkaOffsetsInitializer.latest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )

    ds = env.from_source(
        source,
        watermark_strategy=WatermarkStrategy.for_monotonous_timestamps(),
        source_name="kafka_source",
        type_info=Types.STRING(),
    )

    # --- Pipeline: Parse → Compute Features → Filter None ---
    parsed = ds.map(parse_event, output_type=Types.PICKLED_BYTE_ARRAY())
    features = parsed.map(compute_features, output_type=Types.STRING()).filter(lambda x: x is not None)

    # Print (for debug)
    features.print()

    env.execute("Churn Prediction Feature Processor")


if __name__ == "__main__":
    main()

