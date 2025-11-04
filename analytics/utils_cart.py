# analytics/utils_cart.py
import pandas as pd
from django.utils import timezone
from datetime import timedelta

from analytics.models import UserEvent
from users.models import User

# Event names assumed from your frontend/collector:
# - "add_to_cart", optional "remove_from_cart", "checkout_started", "purchase"
# Properties may include: {"sku": "...", "cart_value": 123.45, "qty": 2}

ABANDON_WINDOW_MIN = 60  # consider as abandoned if no purchase within 60 min of last cart activity

def get_cart_training_frame(cutoff_minutes: int = ABANDON_WINDOW_MIN) -> pd.DataFrame:
    """
    Creates a per-(user, session?) feature frame with a binary 'abandoned' label:
    1 if user had cart activity but no purchase within cutoff_minutes.
    """
    # Pull recent horizon (last 30 days) for training; adjust as you like.
    horizon = timezone.now() - timedelta(days=30)
    events = (
        UserEvent.objects
        .filter(timestamp__gte=horizon)
        .values("user_id", "event_name", "timestamp", "properties")
        .order_by("user_id", "timestamp")
    )

    # Accumulate per-user cart sessions in memory.
    rows = []
    per_user = {}

    def flush_session(user_id):
        s = per_user.get(user_id)
        if not s:
            return
        # Label: abandoned if no purchase within cutoff of last cart event
        abandoned = int(
            s["last_cart_ts"] is not None and
            (s["purchased_ts"] is None or (s["purchased_ts"] - s["last_cart_ts"]).total_seconds() > cutoff_minutes * 60)
        )
        rows.append({
            "user_id": user_id,
            "cart_events": s["cart_events"],
            "items_added": s["items_added"],
            "cart_value_sum": s["cart_value_sum"],
            "time_to_purchase_min": (
                None if s["purchased_ts"] is None or s["last_cart_ts"] is None
                else (s["purchased_ts"] - s["last_cart_ts"]).total_seconds() / 60.0
            ),
            "abandoned": abandoned,
            "last_cart_ts": s["last_cart_ts"],
            "purchased_ts": s["purchased_ts"],
        })

    for ev in events:
        uid = ev["user_id"]
        if uid not in per_user:
            per_user[uid] = {
                "cart_events": 0,
                "items_added": 0,
                "cart_value_sum": 0.0,
                "last_cart_ts": None,
                "purchased_ts": None,
            }

        e = per_user[uid]
        name = ev["event_name"]
        ts = ev["timestamp"]
        props = ev.get("properties") or {}

        if name in ("add_to_cart", "cart_update", "checkout_started"):
            e["cart_events"] += 1
            e["last_cart_ts"] = ts
            e["items_added"] += int(props.get("qty", 1))
            try:
                e["cart_value_sum"] += float(props.get("cart_value", 0.0))
            except Exception:
                pass
        elif name == "purchase":
            # mark purchase time; session ends
            e["purchased_ts"] = ts
            flush_session(uid)
            # reset after purchase to allow next session
            per_user[uid] = {
                "cart_events": 0,
                "items_added": 0,
                "cart_value_sum": 0.0,
                "last_cart_ts": None,
                "purchased_ts": None,
            }

    # flush unfinished sessions
    for uid in list(per_user.keys()):
        flush_session(uid)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Basic imputations
    df["cart_events"] = df["cart_events"].fillna(0)
    df["items_added"] = df["items_added"].fillna(0)
    df["cart_value_sum"] = df["cart_value_sum"].fillna(0.0)
    # derive a useful feature
    df["had_checkout"] = (df["cart_events"] > 0).astype(int)

    # Select features for modeling
    features = df[["cart_events", "items_added", "cart_value_sum", "had_checkout"]].copy()
    features["abandoned"] = df["abandoned"].astype(int)

    # Keep user_id for later joins/predictions
    features["user_id"] = df["user_id"]

    return features
