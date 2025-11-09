# analytics/predict_cart_abandon.py
import os
import sys
import django
import joblib
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
from django.conf import settings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "churn_prediction.settings")
django.setup()

from analytics.utils_cart import get_cart_training_frame
from users.models import User
from analytics.models import SMTPConfiguration

RISK_THRESHOLD = float(os.getenv("CART_ABANDON_THRESHOLD", "0.75"))

def predict_cart_abandon():
    print("🔮 Predicting cart abandonment (batch)...")

    model_path = os.path.join(BASE_DIR, "ml", "models", "shared_models", "cart_model.joblib")
    if not os.path.exists(model_path):
        print("❌ Cart model missing. Train first.")
        return

    model = joblib.load(model_path)
    df = get_cart_training_frame()
    if df.empty:
        print("⚠️ No data for prediction.")
        return

    feature_cols = ["cart_events", "items_added", "cart_value_sum", "had_checkout"]
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        print(f"❌ Missing features: {missing}")
        return

    # SMTP / SES config from DB
    try:
        smtp = SMTPConfiguration.objects.get(smtp_client_name="DEFAULT")
    except SMTPConfiguration.DoesNotExist:
        print("❌ SMTP config 'DEFAULT' not found")
        return

    settings.EMAIL_HOST = smtp.smtp_email_host
    settings.EMAIL_USE_TLS = smtp.smtp_email_use_tls
    settings.EMAIL_PORT = smtp.smtp_email_port
    settings.EMAIL_HOST_USER = smtp.smtp_email_host_user
    settings.EMAIL_HOST_PASSWORD = smtp.smtp_email_host_password

    access_key = smtp.access_key_id
    secret_key = smtp.aws_secret_key
    region = smtp.aws_region
    email_type = smtp.email_type
    email_from = smtp.smtp_email_host_user

    df["abandon_prob"] = model.predict_proba(df[feature_cols])[:, 1]

    high = df[df["abandon_prob"] >= RISK_THRESHOLD]

    for _, row in high.iterrows():
        uid = int(row["user_id"])
        prob = float(row["abandon_prob"])
        try:
            user = User.objects.get(id=uid)
        except User.DoesNotExist:
            continue

        subject = f"🛒 High Cart Abandon Risk: {user.email}"
        body = (
            f"User {user.email} abandonment probability: {prob:.2f}.\n"
            f"Recommended action: send coupon/offer."
        )

        if email_type.upper() in ("SES", "AWS_SES"):
            try:
                ses = boto3.client(
                    "ses",
                    region_name=region,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                )
                msg = MIMEMultipart()
                msg["Subject"] = subject
                msg["From"] = email_from
                msg["To"] = ", ".join(["alerts@example.com"])
                msg.attach(MIMEText(body, "plain"))

                ses.send_raw_email(
                    Source=email_from,
                    Destinations=["alerts@example.com"],
                    RawMessage={"Data": msg.as_string()},
                )
                print(f"✅ Alert sent for {user.email} ({prob:.2f})")
            except ClientError as e:
                print(f"❌ SES failed: {e.response['Error']['Message']}")
        else:
            print(f"ℹ Unsupported email type: {email_type}")

    print(f"✅ Processed {len(high)} high-risk users.")

if __name__ == "__main__":
    predict_cart_abandon()
