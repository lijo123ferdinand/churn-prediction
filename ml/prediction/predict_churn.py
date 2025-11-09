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

# --- Django setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "churn_prediction.settings")
django.setup()

from analytics.utils import get_user_features
from users.models import User
from analytics.models import SMTPConfiguration  # adjust to your app name


def predict_churn():
    """
    Load the trained churn model, predict churn probabilities,
    update user records, and send alerts for high-risk users via AWS SES.
    """
    print("🔮 Starting churn prediction...")

    model_path = os.path.join(BASE_DIR, "ml", "models", "churn_model.pkl")

    if not os.path.exists(model_path):
        print("❌ Model file not found, skipping prediction.")
        return

    # Load the model
    model = joblib.load(model_path)
    print("✅ Model loaded successfully.")

    # Extract features
    df = get_user_features()
    if df.empty:
        print("⚠️ No user data available for churn prediction.")
        return

    feature_cols = ['days_since_last_login', 'avg_order_value', 'purchase_frequency']
    missing_cols = [col for col in feature_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ Missing required feature columns: {missing_cols}")
        return

    # --- 🔧 Load SMTP/SES Configuration from DB ---
    try:
        smtp_config = SMTPConfiguration.objects.get(smtp_client_name="DEFAULT")
    except SMTPConfiguration.DoesNotExist:
        print("❌ SMTP configuration 'DEFAULT' not found in DB")
        return

    smtp_data = {
        'smtp_email_host': smtp_config.smtp_email_host,
        'smtp_email_use_tls': smtp_config.smtp_email_use_tls,
        'smtp_email_port': smtp_config.smtp_email_port,
        'smtp_email_host_user': smtp_config.smtp_email_host_user,
        'smtp_email_host_password': smtp_config.smtp_email_host_password,
        'access_key_id': smtp_config.access_key_id,
        'aws_secret_key': smtp_config.aws_secret_key,
        'aws_region': smtp_config.aws_region,
        'email_type': smtp_config.email_type,
    }

    # Apply Django settings dynamically
    settings.EMAIL_HOST = smtp_data.get('smtp_email_host')
    settings.EMAIL_USE_TLS = smtp_data.get('smtp_email_use_tls')
    settings.EMAIL_PORT = smtp_data.get('smtp_email_port')
    settings.EMAIL_HOST_USER = smtp_data.get('smtp_email_host_user')
    settings.EMAIL_HOST_PASSWORD = smtp_data.get('smtp_email_host_password')

    smtp_server = settings.EMAIL_HOST
    smtp_port = settings.EMAIL_PORT
    email_from = settings.EMAIL_HOST_USER
    access_key = smtp_data.get('access_key_id')
    aws_secret_key = smtp_data.get('aws_secret_key')
    aws_region = smtp_data.get('aws_region')
    email_type = smtp_data.get('email_type')

    print(f"📡 Email system configured: {email_type} ({smtp_server})")

    # Predict churn
    df['churn_probability'] = model.predict_proba(df[feature_cols])[:, 1]

    updated_count = 0
    high_risk_users = []

    for _, row in df.iterrows():
        user_id = row['user_id']
        churn_prob = float(row['churn_probability'])

        try:
            user = User.objects.get(id=int(user_id))
        except (User.DoesNotExist, ValueError):
            print(f"⚠️ User with id {user_id} not found or invalid, skipping.")
            continue

        # Update user
        user.churn_score = churn_prob
        user.is_active = churn_prob < 0.5
        user.save()
        updated_count += 1

        # High-risk users
        if churn_prob < 0.8:
            high_risk_users.append((user.email, churn_prob))
            subject = f"⚠️ High Churn Risk: {user.email}"
            body = (
                f"User {user.email} has a churn probability of {churn_prob:.2f}.\n"
                "Action recommended: send re-engagement offer or discount."
            )

            # --- ✉️ Send via AWS SES ---
            if email_type.upper() in ("SES", "AWS_SES"):
                try:
                    print("📤 Creating boto3 SES client...")
                    ses_client = boto3.client(
                        'ses',
                        region_name=aws_region,
                        aws_access_key_id=access_key,
                        aws_secret_access_key=aws_secret_key
                    )

                    msg = MIMEMultipart()
                    msg["Subject"] = subject
                    msg["From"] = email_from
                    msg["To"] = ", ".join(
                        ["lijo_ferdinand@thbs.com"]
                    )
                    msg.attach(MIMEText(body, "plain"))

                    print("🚀 Sending email using SES...")
                    response = ses_client.send_raw_email(
                        Source=email_from,
                        Destinations=["lijo_ferdinand@thbs.com"],
                        RawMessage={"Data": msg.as_string()},
                    )
                    print(f"✅ Email sent via SES to {user.email}")
                    print(response)

                except ClientError as e:
                    print(f"❌ Failed to send email via SES: {e.response['Error']['Message']}")
            else:
                print(f"⚠️ Email type '{email_type}' not supported for {user.email}")

    print(f"✅ Updated churn data for {updated_count} users.")
    if high_risk_users:
        print(f"🚨 {len(high_risk_users)} users flagged as high-risk:")
        for email, prob in high_risk_users:
            print(f"   - {email}: {prob:.2f}")
    else:
        print("✅ No high-risk users detected.")


if __name__ == "__main__":
    predict_churn()
