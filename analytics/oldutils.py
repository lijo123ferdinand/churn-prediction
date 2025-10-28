from django.utils import timezone
import pandas as pd
from users.models import User

def get_user_features():
    users = User.objects.all()
    data = []

    for u in users:
        # Use timezone-aware datetime
        now = timezone.now()
        last_login = u.last_login or u.signup_date

        days_since_last_login = (now - last_login).days
        avg_order_value = u.total_spent / u.total_orders if u.total_orders > 0 else 0
        purchase_frequency = u.total_orders / max((now - u.signup_date).days, 1)

        data.append({
            "user_id": u.id,
            "days_since_last_login": days_since_last_login,
            "avg_order_value": avg_order_value,
            "purchase_frequency": purchase_frequency,
        })

    return pd.DataFrame(data)
