import os
import sys
import django
import joblib
import pandas as pd

# --- Django setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "churn_prediction.settings")
django.setup()

from analytics.utils import get_user_features
from users.models import User


def predict_churn():
    """Load the trained churn model, predict churn, and update user records."""
    print("✅ Loaded trained churn model.")
    model_path = os.path.join(BASE_DIR, "analytics", "churn_model.pkl")

    if not os.path.exists(model_path):
        print("❌ Model file not found, skipping prediction.")
        return

    model = joblib.load(model_path)
    df = get_user_features()
    if df.empty:
        print("⚠️ No user data available for prediction.")
        return

    df['churn_probability'] = model.predict_proba(
        df[['days_since_last_login', 'avg_order_value', 'purchase_frequency']]
    )[:, 1]

    updated_count = 0

    for index, row in df.iterrows():
        user_id = str(row['user_id']).replace('user_', '')  # handle 'user_105'
        try:
            user = User.objects.get(id=int(user_id))
        except User.DoesNotExist:
            print(f"⚠️ User with id {user_id} not found, skipping.")
            continue

        user.churn_score = float(row['churn_probability'])
        user.is_active = row['churn_probability'] < 0.5
        user.save()
        updated_count += 1

    print(f"✅ Predicted churn for {updated_count} users and updated their records.")


# Optional: allow manual execution
if __name__ == "__main__":
    predict_churn()
