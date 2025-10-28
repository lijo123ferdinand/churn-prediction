import os
import sys
import django
import joblib
import pandas as pd
from django.core.mail import send_mail

# --- Django setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "churn_prediction.settings")
django.setup()

from analytics.utils import get_user_features
from users.models import User


def predict_churn():
    """Load the trained churn model, predict churn, update user records, and send alerts."""
    print("✅ Starting churn prediction...")
    model_path = os.path.join(BASE_DIR, "analytics", "churn_model.pkl")

    if not os.path.exists(model_path):
        print("❌ Model file not found, skipping prediction.")
        return

    # Load model
    model = joblib.load(model_path)

    # Get user features
    df = get_user_features()
    if df.empty:
        print("⚠️ No user data available for prediction.")
        return

    # Predict churn probability
    df['churn_probability'] = model.predict_proba(
        df[['days_since_last_login', 'avg_order_value', 'purchase_frequency']]
    )[:, 1]

    updated_count = 0

    # Iterate through all users and update records
    for index, row in df.iterrows():
        user_id = row['user_id']
        try:
            user = User.objects.get(id=user_id)
            churn_prob = float(row['churn_probability'])

            user.churn_score = churn_prob
            user.is_active = churn_prob < 0.5
            user.save()
            updated_count += 1

            # 🚨 Send notification if churn probability > 0.8
            if churn_prob > 0.8:
                send_mail(
                    subject=f"⚠️ High Churn Risk Detected for {user.email}",
                    message=(
                        f"User {user.email} has a churn probability of {churn_prob:.2f}.\n"
                        "Consider taking engagement action (discounts, reactivation email, etc)."
                    ),
                    from_email=os.getenv("EMAIL_HOST_USER", "your_email@gmail.com"),
                    recipient_list=["lijoferdinand@gmail.com"],  # or user.email if you want to email the user directly
                    fail_silently=False,
                )
                print(f"📧 Email alert sent for high-churn user: {user.email}")

        except User.DoesNotExist:
            print(f"⚠️ User with id {user_id} not found, skipping.")

    print(f"✅ Predicted churn for {updated_count} users and updated their records.")


if __name__ == "__main__":
    predict_churn()
