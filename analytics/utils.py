from django.utils import timezone
from analytics.models import UserEvent
import pandas as pd

def get_user_features():
    now = timezone.now()
    data = []

    # Get distinct users from event data
    users = UserEvent.objects.values_list('user_id', flat=True).distinct()

    for uid in users:
        events = UserEvent.objects.filter(user_id=uid)
        if not events.exists():
            continue

        # Derive basic features
        last_event = events.latest('timestamp')
        first_event = events.earliest('timestamp')
        total_events = events.count()

        days_since_last_login = (now - last_event.timestamp).days
        avg_order_value = 0  # Placeholder, no purchase data yet
        purchase_frequency = total_events / max((now - first_event.timestamp).days, 1)

        data.append({
            "user_id": uid,
            "days_since_last_login": days_since_last_login,
            "avg_order_value": avg_order_value,
            "purchase_frequency": purchase_frequency,
        })

    return pd.DataFrame(data)
