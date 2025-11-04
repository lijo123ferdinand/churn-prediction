# analytics/flink_cart_abandon_job.py
import os
import json
import time
import joblib
import boto3
import redis
import numpy as np
from datetime import datetime, timezone, timedelta

from pyflink.common import Types, Time
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream import StreamExecutionEnvironment, TimeCharacteristic
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer
from pyflink.datastream.functions import KeyedProcessFunction, RuntimeContext
from pyflink.common.watermark_strategy import WatermarkStrategy

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from botocore.exceptions import ClientError

# --- Config via env ---
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "user_events")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6380"))
ABANDON_WINDOW_MIN = int(os.getenv("ABANDON_WINDOW_MIN", "60"))
RISK_THRESHOLD = float(os.getenv("CART_ABANDON_THRESHOLD", "0.75"))

# S3 model
S3_BUCKET = os.getenv("S3_BUCKET", "ml-models")
S3_KEY_CART_MODEL = os.getenv("S3_KEY_CART_MODEL", "cart_abandon/cart_model.joblib")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# SES / alerts
ALERTS_EMAIL_FROM = os.getenv("ALERTS_EMAIL_FROM", "no-reply@example.com")
ALERTS_EMAIL_TO = os.getenv("ALERTS_EMAIL_TO", "alerts@example.com")

LOCAL_MODEL_PATH = "/shared_models/cart_model.joblib"
def load_model_local():
    if not os.path.exists(LOCAL_MODEL_PATH):
        raise FileNotFoundError(f"❌ Model not found at {LOCAL_MODEL_PATH}. Did you run train_cart_model.py?")
    return joblib.load(LOCAL_MODEL_PATH)

def download_model():
    session = boto3.session.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    s3 = session.client("s3", endpoint_url=S3_ENDPOINT_URL) if S3_ENDPOINT_URL else session.client("s3")
    s3.download_file(S3_BUCKET, S3_KEY_CART_MODEL, LOCAL_MODEL_PATH)
    return joblib.load(LOCAL_MODEL_PATH)

def send_email(subject: str, body: str):
    try:
        ses = boto3.client(
            "ses",
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = ALERTS_EMAIL_FROM
        msg["To"] = ALERTS_EMAIL_TO
        msg.attach(MIMEText(body, "plain"))

        ses.send_raw_email(
            Source=ALERTS_EMAIL_FROM,
            Destinations=[ALERTS_EMAIL_TO],
            RawMessage={"Data": msg.as_string()},
        )
    except ClientError as e:
        print(f"❌ SES error: {e.response['Error']['Message']}")

class CartAbandonProcess(KeyedProcessFunction):

    def open(self, runtime_context: RuntimeContext):
        # Load model once on open
        self.model = load_model_local()
        self.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

        # ValueState: last cart ts, items, value, has_purchase flag
        state_desc_ts = runtime_context.get_state_descriptor(
            "last_cart_ts", Types.LONG()  # epoch millis
        )
        state_desc_items = runtime_context.get_state_descriptor(
            "items_added", Types.INT()
        )
        state_desc_value = runtime_context.get_state_descriptor(
            "cart_value_sum", Types.FLOAT()
        )
        state_desc_purchased = runtime_context.get_state_descriptor(
            "has_purchased", Types.BOOLEAN()
        )
        state_desc_timer = runtime_context.get_state_descriptor(
            "timer_ts", Types.LONG()
        )

        self.last_cart_ts = runtime_context.get_state(state_desc_ts)
        self.items_added = runtime_context.get_state(state_desc_items)
        self.cart_value_sum = runtime_context.get_state(state_desc_value)
        self.has_purchased = runtime_context.get_state(state_desc_purchased)
        self.timer_ts = runtime_context.get_state(state_desc_timer)

    def process_element(self, value, ctx: 'KeyedProcessFunction.Context'):
        """
        value is a JSON string
        key = user_id
        """
        try:
            ev = json.loads(value)
        except Exception:
            return

        user_id = ev.get("user_id")
        if user_id is None:
            return

        name = ev.get("event_name", "")
        ts_str = ev.get("timestamp") or datetime.now(timezone.utc).isoformat()
        props = ev.get("properties") or {}
        try:
            event_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            event_ts = datetime.now(timezone.utc)
        event_ms = int(event_ts.timestamp() * 1000)

        # Load current state
        last_cart = self.last_cart_ts.value() or 0
        items = self.items_added.value() or 0
        val = self.cart_value_sum.value() or 0.0
        purchased = self.has_purchased.value() or False

        # Handle events
        if name in ("add_to_cart", "cart_update", "checkout_started"):
            qty = int(props.get("qty", 1))
            cart_val = float(props.get("cart_value", 0.0))
            items += qty
            val += cart_val
            last_cart = event_ms
            purchased = False

            # Register/refresh timer for abandonment check
            # Processing time timer at now + window
            abandon_ms = int(ABANDON_WINDOW_MIN * 60 * 1000)
            fire_at = ctx.timer_service().current_processing_time() + abandon_ms
            ctx.timer_service().register_processing_time_timer(fire_at)
            self.timer_ts.update(fire_at)

        elif name == "purchase":
            # mark purchased; cancel pending timer by just clearing state
            purchased = True
            items = 0
            val = 0.0
            last_cart = 0
            # No explicit timer cancel in Python API; we just ignore when it fires.

        # Update state
        self.last_cart_ts.update(last_cart)
        self.items_added.update(items)
        self.cart_value_sum.update(val)
