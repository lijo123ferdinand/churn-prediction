import os
import json
import redis
import joblib
import numpy as np
import requests
from datetime import datetime, timezone

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import MapFunction, RuntimeContext
from pyflink.common import Types
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.watermark_strategy import WatermarkStrategy
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
CHURN_THRESHOLD = 0.08  # email when churn score < 0.08

SMTP_API_URL = "http://localhost:8000/analytics/smtp-config/"
USE_SES = True

KAFKA_BOOTSTRAP = "localhost:9092"
KAFKA_TOPIC = "user_events"

REDIS_HOST = "localhost"
REDIS_PORT = 6380

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "app", "churn_model.joblib")

ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "lijo_ferdinand@thbs.com")


# ---------------------------------------------------------
# FETCH SMTP
# ---------------------------------------------------------
def load_smtp_from_backend():
    try:
        print("Fetching SMTP config...")
        res = requests.get(SMTP_API_URL, timeout=5)
        return res.json()
    except Exception as e:
        print("❌ Failed fetching SMTP config:", e)
        return None


# ---------------------------------------------------------
# CHURN PROCESSOR CLASS  (just like your cart job)
# ---------------------------------------------------------
class ChurnProcessor(MapFunction):

    def open(self, ctx: RuntimeContext):
        print("🔄 Loading churn model:", MODEL_PATH)

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}")

        self.model = joblib.load(MODEL_PATH)
        print("✅ Model loaded.")

        print(f"🔗 Connecting Redis {REDIS_HOST}:{REDIS_PORT}")
        self.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        self.redis.ping()
        print("✅ Redis OK.")

        # Load SMTP
        self.smtp = load_smtp_from_backend()
        if self.smtp is None:
            raise RuntimeError("❌ Could not load SMTP config")

        print("SMTP CONFIG:", self.smtp)

        # SES client
        if USE_SES:
            import boto3
            self.ses = boto3.client(
                "ses",
                region_name=self.smtp["region"],
                aws_access_key_id=self.smtp["aws_access_key"],
                aws_secret_access_key=self.smtp["aws_secret"],
            )
        else:
            self.ses = None

        print("✅ Processor ready.")

    # -----------------------------------------------------
    # EMAIL SENDER
    # -----------------------------------------------------
    def send_email(self, subject, body):
        # log locally
        try:
            with open("churn_email_alerts.log", "a") as f:
                f.write("\n" + "=" * 60 + "\n")
                f.write(f"📩 AT: {datetime.now(timezone.utc).isoformat()}\n")
                f.write(f"SUBJECT: {subject}\n{body}\n")
                f.write("=" * 60 + "\n")
        except:
            pass

        if not USE_SES:
            print("📩 MOCK EMAIL:", subject, body)
            return

        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = self.smtp["username"]
            msg["To"] = ALERT_EMAIL_TO
            msg.attach(MIMEText(body, "plain"))

            self.ses.send_raw_email(
                Source=self.smtp["username"],
                Destinations=[ALERT_EMAIL_TO],
                RawMessage={"Data": msg.as_string()},
            )
            print("✅ EMAIL SENT:", subject)

        except Exception as e:
            print("❌ SES ERROR:", e)

    # -----------------------------------------------------
    # MAIN MAP FUNCTION
    # -----------------------------------------------------
    def map(self, raw):
        try:
            event = json.loads(raw)
        except:
            return None

        if "user_id" not in event:
            return None

        user_id = event["user_id"]
        event_name = event.get("event_name", "")

        # timestamp handling
        ts_raw = event.get("timestamp")
        if not ts_raw:
            ts = datetime.now(timezone.utc)
        else:
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except:
                ts = datetime.now(timezone.utc)

        ts_str = ts.isoformat() + "Z"

        # Redis state lookup
        user_key = f"user:{user_id}"
        existing = self.redis.hgetall(user_key)

        event_count = int(existing.get(b"event_count", 0))

        last_ts = None
        if b"last_event_time" in existing:
            try:
                last_ts = datetime.fromisoformat(existing[b"last_event_time"].decode())
            except:
                pass

        event_count += 1
        time_diff = (ts - last_ts).total_seconds() / 3600 if last_ts else 0

        # ML prediction
        features = np.array([[event_count, time_diff]])
        churn_prob = float(self.model.predict_proba(features)[0][1])

        # Save to Redis
        self.redis.hset(
            user_key,
            mapping={
                "event_count": event_count,
                "last_event_time": ts.isoformat(),
                "churn_score": churn_prob,
            },
        )

        print(f"📊 User {user_id} churn={churn_prob:.4f}")

        # -----------------------------------------------------
        # EMAIL ALERT
        # -----------------------------------------------------
        if churn_prob < CHURN_THRESHOLD:
            self.send_email(
                subject=f"⚠️ LOW CHURN SCORE ALERT — User {user_id}",
                body=(
                    f"User ID: {user_id}\n"
                    f"Events: {event_count}\n"
                    f"Hours since last event: {time_diff:.2f}\n"
                    f"Churn Score: {churn_prob:.4f}\n"
                    f"Threshold: {CHURN_THRESHOLD}\n"
                ),
            )

        return json.dumps({
            "user_id": user_id,
            "event_name": event_name,
            "event_count": event_count,
            "churn_score": churn_prob,
            "timestamp": ts_str,
        })


# ---------------------------------------------------------
# FLINK JOB
# ---------------------------------------------------------
def main():
    print("🚀 Starting Churn Flink Job...")

    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(1)

    source = (
        KafkaSource.builder()
        .set_bootstrap_servers(KAFKA_BOOTSTRAP)
        .set_topics(KAFKA_TOPIC)
        .set_group_id("flink_churn_analytics")
        .set_starting_offsets(KafkaOffsetsInitializer.latest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )

    stream = env.from_source(
        source,
        WatermarkStrategy.no_watermarks(),
        "kafka_source",
        type_info=Types.STRING(),
    )

    output = stream.map(ChurnProcessor(), output_type=Types.STRING())

    output.print()

    env.execute("Realtime Churn Processor")


if __name__ == "__main__":
    main()
