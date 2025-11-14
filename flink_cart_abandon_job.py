import os
import json
import redis
import joblib
import numpy as np
import traceback
import requests

from datetime import datetime, timezone

from pyflink.common import Types
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer
from pyflink.datastream.functions import KeyedProcessFunction, RuntimeContext
from pyflink.datastream.state import ValueStateDescriptor
from pyflink.common.watermark_strategy import WatermarkStrategy
SMTP_CONFIG = None

# SMTP_API_URL = os.getenv("SMTP_API_URL")
SMTP_API_URL = "http://localhost:8000/analytics/smtp-config/"
    
# --- Optional SES (only if you really need it)
# USE_SES = os.getenv("USE_SES", "false").lower() in ("1", "true", "yes")
USE_SES = True
if USE_SES:
    import boto3
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from botocore.exceptions import ClientError

# ──────────────────────────────────────────────────────────────
# ENV CONFIG
# ──────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")   # <-- set to 172.18.0.4:9092 if needed
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "cart_events")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6380"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "shared_models", "cart_model.joblib")
ABANDON_WINDOW_MIN = int(os.getenv("ABANDON_WINDOW_MIN", "6"))
RISK_THRESHOLD = float(os.getenv("CART_ABANDON_THRESHOLD", "0.75"))

# AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
# AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
# AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
# ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "no-reply@example.com")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "lijo_ferdinand@thbs.com")

def load_smtp_from_backend():
    try:
        res = requests.get(SMTP_API_URL, timeout=5)
        data = res.json()
        print("SMTP config fetched")

        return data

    except Exception as e:
        print("Failed to fetch SMTP config:", e)
        return None
# ──────────────────────────────────────────────────────────────
# EMAIL SENDER
# ──────────────────────────────────────────────────────────────
def send_email(subject: str, body: str):
    # Log to file
    try:
        with open("email_alerts.log", "a") as f:
            f.write("\n" + "="*60 + "\n")
            f.write(f"📩 EMAIL SENT AT: {datetime.now(timezone.utc).isoformat()}\n")
            f.write(f"SUBJECT: {subject}\n")
            f.write(body + "\n")
            f.write("="*60 + "\n")
        print(f"📝 Email logged to email_alerts.log")
    except Exception as log_err:
        print(f"⚠️ Failed to write email log: {log_err}")

    # If SES disabled → print mock
    if not USE_SES:
        print(f"📩 EMAIL (mock)\nSUBJECT: {subject}\n{body}")
        return

    # Real SES
    try:
        ses = boto3.client(
            "ses",
            region_name=SMTP_CONFIG["region"],
            aws_access_key_id=SMTP_CONFIG["aws_access_key"],
            aws_secret_access_key=SMTP_CONFIG["aws_secret"],
        )

        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = SMTP_CONFIG["username"]
        msg["To"] = ALERT_EMAIL_TO
        msg.attach(MIMEText(body, "plain"))

        ses.send_raw_email(
            Source=SMTP_CONFIG["username"],
            Destinations=[ALERT_EMAIL_TO],
            RawMessage={"Data": msg.as_string()},
        )

        print(f"✅ Email sent: {subject}")

    except Exception as e:
        print(f"❌ SES Error: {e}")

    except Exception as e:
        print(f"❌ SES Error: {e}")

# ──────────────────────────────────────────────────────────────
# FLINK PROCESS FUNCTION
# ──────────────────────────────────────────────────────────────
class CartAbandonProcessor(KeyedProcessFunction):

    def open(self, ctx: RuntimeContext):
        try:
            print("🔄 Loading cart abandonment model:", MODEL_PATH)
            if not os.path.exists(MODEL_PATH):
                raise FileNotFoundError(f"Model not found at {MODEL_PATH}")

            self.model = joblib.load(MODEL_PATH)
            print("✅ Model loaded.")

            print(f"🔗 Connecting Redis {REDIS_HOST}:{REDIS_PORT}")
            self.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
            self.redis.ping()
            print("✅ Redis OK.")

            # Proper ValueStateDescriptors
            self.last_cart_ts = ctx.get_state(ValueStateDescriptor("last_cart_ts", Types.LONG()))
            self.items_added = ctx.get_state(ValueStateDescriptor("items_added", Types.INT()))
            self.cart_value_sum = ctx.get_state(ValueStateDescriptor("cart_value_sum", Types.FLOAT()))
            self.has_purchased = ctx.get_state(ValueStateDescriptor("has_purchased", Types.BOOLEAN()))
            self.timer_ts = ctx.get_state(ValueStateDescriptor("timer_ts", Types.LONG()))
            print("✅ State initialized.")

        except Exception as e:
            print("❌ open() failed:", e)
            traceback.print_exc()
            # re-raise to fail fast and show in task logs
            raise

    def process_element(self, value, ctx: 'KeyedProcessFunction.Context'):
        try:
            event = json.loads(value)
        except Exception:
            return

        user_id = event.get("user_id")
        if not user_id:
            return

        event_name = event.get("event_name", "")
        props = event.get("properties", {}) or {}
        ts_str = event.get("timestamp", datetime.now(timezone.utc).isoformat())

        try:
            event_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            event_ts = datetime.now(timezone.utc)

        event_ms = int(event_ts.timestamp() * 1000)

        last_cart = self.last_cart_ts.value() or 0
        items = self.items_added.value() or 0
        cart_value = self.cart_value_sum.value() or 0.0
        purchased = self.has_purchased.value() or False

        # Debug one-liner for each message
        print(f"📥 [{user_id}] {event_name} @ {ts_str} | items={items} value={cart_value} purchased={purchased}")

        # ─── Cart activity ──────────────────────────────────
        if event_name in ("add_to_cart", "cart_update", "checkout_started"):
            qty = int(props.get("qty", 1))
            val = float(props.get("cart_value", 0.0))
            items += qty
            cart_value += val
            last_cart = event_ms
            purchased = False

            # abandon_ms = ABANDON_WINDOW_MIN * 60 * 1000
            abandon_ms = ABANDON_WINDOW_MIN * 1000
            fire_at = ctx.timer_service().current_processing_time() + abandon_ms
            ctx.timer_service().register_processing_time_timer(fire_at)
            print(f"🕐 Timer registered for user {user_id}, fires in {abandon_ms/1000:.1f} sec (at {fire_at})")

            self.timer_ts.update(fire_at)

            # live score
            features = np.array([[items, cart_value, 1 if items > 0 else 0, 1]])
            try:
                prob = float(self.model.predict_proba(features)[0][1])
            except Exception as e:
                print(f"⚠️ predict_proba failed: {e}")
                prob = 0.0

            self.redis.hset(
                f"user:{user_id}",
                mapping={
                    "cart_abandon_score": prob,
                    "cart_items": items,
                    "cart_value_sum": cart_value,
                    "cart_last_update": event_ts.isoformat(),
                },
            )
            print(f"🟢 [{user_id}] live_prob={prob:.2f} items={items} value={cart_value:.2f}")

        # ─── Purchase resets ────────────────────────────────
        elif event_name == "purchase":
            purchased = True
            last_cart = 0
            items = 0
            cart_value = 0.0
            print(f"✅ [{user_id}] purchase -> reset.")

        # update state
        self.last_cart_ts.update(last_cart)
        self.items_added.update(items)
        self.cart_value_sum.update(cart_value)
        self.has_purchased.update(purchased)
        
    # ✅ RETURN OUTPUT TO THE FLINK PIPELINE HERE
        yield json.dumps({
            "user_id": user_id,
            "event": event_name,
            "items": items,
            "cart_value": cart_value,
            "ts": ts_str
    }, separators=(",", ":"))

    def on_timer(self, timestamp, ctx: 'KeyedProcessFunction.OnTimerContext'):
        user_id = ctx.get_current_key()

        last_cart = self.last_cart_ts.value() or 0
        items = self.items_added.value() or 0
        cart_value = self.cart_value_sum.value() or 0.0
        purchased = self.has_purchased.value() or False

        print(f"⏰ TIMER [{user_id}] purchased={purchased} last_cart={last_cart} items={items}")

        if purchased or last_cart == 0 or items == 0:
            yield from ()
            return

        features = np.array([[items, cart_value, 1 if items > 0 else 0, 1]])
        try:
            prob = float(self.model.predict_proba(features)[0][1])
        except Exception as e:
            print(f"⚠️ predict_proba failed on timer: {e}")
            prob = 0.0

        self.redis.hset(
            f"user:{user_id}",
            mapping={
                "cart_abandon_score": prob,
                "cart_abandon_alerted_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        print(f"🚨 TIMER ALERT [{user_id}] prob={prob:.2f} items={items} value={cart_value:.2f}")

        # if prob >= RISK_THRESHOLD:
        if True:
            send_email(
                subject=f"🛒 CART ABANDONMENT ALERT: User {user_id} ({prob:.2f})",
                body=(
                    f"User {user_id} may abandon cart.\n"
                    f"Items: {items}\n"
                    f"Cart value: {cart_value}\n"
                    f"Score: {prob:.2f}\n"
                    f"Window: {ABANDON_WINDOW_MIN} seconds inactivity\n"
                ),
            )

        # clear session state
        self.last_cart_ts.clear()
        self.items_added.clear()
        self.cart_value_sum.clear()
        self.has_purchased.clear()
         # ✅ Always yield (even if it's empty output)
        yield json.dumps({
            "user_id": user_id,
            "event": "timer_fired",
            "abandon_prob": prob,
            "items": items,
            "cart_value": cart_value
        }, separators=(",", ":"))

# ──────────────────────────────────────────────────────────────
# FLINK JOB SETUP
# ──────────────────────────────────────────────────────────────
def main():
    try:
        print("🚀 Starting Flink Cart Abandonment Job...")
        print(f"📌 MODEL PATH: {MODEL_PATH}")
        print(f"📌 Kafka: {KAFKA_BOOTSTRAP} / {KAFKA_TOPIC}")
        print(f"📌 Redis: {REDIS_HOST}:{REDIS_PORT}")
        print(f"📌 Abandon window: {ABANDON_WINDOW_MIN} seconds  Threshold: {RISK_THRESHOLD}")
        global SMTP_CONFIG

        SMTP_CONFIG = load_smtp_from_backend()
        print("SMTP LOADED:", SMTP_CONFIG)
        if SMTP_CONFIG is None:
            raise RuntimeError("❌ SMTP CONFIG NOT LOADED — Cannot send emails.")




        env = StreamExecutionEnvironment.get_execution_environment()
        env.set_parallelism(1)

        source = (
            KafkaSource.builder()
            .set_topics(KAFKA_TOPIC)
            .set_group_id("flink_cart_abandon")
            .set_bootstrap_servers(KAFKA_BOOTSTRAP)
            .set_starting_offsets(KafkaOffsetsInitializer.latest())
            .set_value_only_deserializer(SimpleStringSchema())
            .build()
        )

        stream = env.from_source(
            source,
            WatermarkStrategy.no_watermarks(),
            "kafka_source"
        )

        stream \
            .key_by(lambda raw: json.loads(raw).get("user_id")) \
            .process(CartAbandonProcessor(), output_type=Types.STRING()).print()

        print("✅ Initialized. Executing job… (waiting for events)")
        env.execute("Cart Abandonment Realtime Processor")

    except Exception as e:
        print("❌ Job failed to start:", e)
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
