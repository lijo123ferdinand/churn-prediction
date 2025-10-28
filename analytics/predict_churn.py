import os
import sys
import django
import joblib
import pandas as pd
from django.utils import timezone

# --- Django setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "churn_prediction.settings")
django.setup()

from analytics.utils import get_user_features
from users.models import User

# --- Load trained model ---
model_path = os.path.join(BASE_DIR, "analytics", "churn_model.pkl")

if not os.path.exists(model_path):
    print("❌ No trained model found. Train the model first.")
    sys.exit(1)

print("✅ Loaded trained churn model.")
model = joblib.load(model_path)

# --- Load features ---
df = get_user_features()
if df.empty:
    print("⚠️ No user features found for prediction. Exiting.")
    sys.exit(0)

required_cols = ['days_since_last_login', 'avg_order_value', 'purchase_frequency']
missing = [c for c in required_cols if c not in df.columns]
if missing:
    print(f"⚠️ Missing columns in features: {missing}")
    sys.exit(1)

# --- Predict churn probability ---
df['churn_probability'] = model.predict_proba(df[required_cols])[:, 1]

# --- Update user table ---
updated_count = 0
for index, row in df.iterrows():
    user_id = str(row['user_id']).replace('user_', '')  # remove 'user_' prefix if present
    try:
        user = User.objects.get(id=int(user_id))
    except User.DoesNotExist:
        print(f"⚠️ User with id {user_id} not found, skipping.")
        continue

    user.churn_score = float(row['churn_probability'])
    user.is_active = row['churn_probability'] < 0.5
    user.save()

print(f"✅ Predicted churn for {updated_count} users and updated their records.")
