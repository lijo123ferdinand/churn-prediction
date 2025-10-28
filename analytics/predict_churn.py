import os
import sys
import django
import joblib
from django.core.mail import send_mail
import pandas as pd
from django.conf import settings

# --- Django setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "churn_prediction.settings")
django.setup()

from analytics.utils import get_user_features
from users.models import User


def predict_churn():
    """
    Load the trained churn model, predict churn probabilities,
    update user records, and send alerts for high-risk users.
    """
    print("🔮 Starting churn prediction...")

    model_path = os.path.join(BASE_DIR, "analytics", "churn_model.pkl")

    if not os.path.exists(model_path):
        print("❌ Model file not found, skipping prediction.")
        return

    # Load trained model
    model = joblib.load(model_path)
    print("✅ Model loaded successfully.")

    # Extract user features
    df = get_user_features()
    if df.empty:
        print("⚠️ No user data available for churn prediction.")
        return

    # Ensure necessary columns are present
    feature_cols = ['days_since_last_login', 'avg_order_value', 'purchase_frequency']
    missing_cols = [col for col in feature_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ Missing required feature columns: {missing_cols}")
        return

    # Predict churn probabilities
    df['churn_probability'] = model.predict_proba(df[feature_cols])[:, 1]

    updated_count = 0
    high_risk_users = []

    for _, row in df.iterrows():
        user_id = row['user_id']
        churn_prob = float(row['churn_probability'])

        try:
            # Make sure IDs are numeric (since Kafka can send string IDs)
            user = User.objects.get(id=int(user_id))
        except (User.DoesNotExist, ValueError):
            print(f"⚠️ User with id {user_id} not found or invalid, skipping.")
            continue

        # Update churn-related fields
        user.churn_score = churn_prob
        user.is_active = churn_prob < 0.5
        user.save()
        updated_count += 1
        print(churn_prob)


        # Send notification for high churn risk users
        if churn_prob < 0.8:
            print(churn_prob)
            high_risk_users.append((user.email, churn_prob))
            try:
                send_mail(
                    subject=f"⚠️ High Churn Risk: {user.email}",
                    message=(
                        f"User {user.email} has a churn probability of {churn_prob:.2f}.\n"
                        "Action recommended: send re-engagement offer or discount."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=["lijoferdinand@gmail.com","lijo_ferdinand@thbs.com"],  # or [user.email]
                    fail_silently=True,
                )
                print(f"📧 Alert email sent for {user.email} (churn {churn_prob:.2f})")
            except Exception as e:
                print(f"❌ Failed to send email to {user.email}: {e}")

    print(f"✅ Updated churn data for {updated_count} users.")
    if high_risk_users:
        print(f"🚨 {len(high_risk_users)} users flagged as high-risk:")
        for email, prob in high_risk_users:
            print(f"   - {email}: {prob:.2f}")
    else:
        print("✅ No high-risk users detected.")


if __name__ == "__main__":
    predict_churn()
