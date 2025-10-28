import os
import sys
import django
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
import joblib

# --- Django setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "churn_prediction.settings")
django.setup()

from analytics.utils import get_user_features

def train_churn_model():
    """
    Train churn prediction model using user feature data
    and save the trained model to churn_model.pkl
    """

    print("🚀 Starting churn model training...")

    # Load features from your custom util
    df = get_user_features()
    if df.empty:
        print("⚠️ No user data available for training. Skipping.")
        return

    # Create churn label
    df['churn'] = (df['days_since_last_login'] > 30).astype(int)

    # Select features
    feature_cols = ['days_since_last_login', 'avg_order_value', 'purchase_frequency']
    X = df[feature_cols]
    y = df['churn']

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Model choice (XGBoost recommended)
    model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss'
    )

    # Fit model
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    # Print metrics
    print("📊 Classification Report:")
    print(classification_report(y_test, y_pred))

    # Save model
    model_path = os.path.join(BASE_DIR, "analytics", "churn_model.pkl")
    joblib.dump(model, model_path)

    print(f"✅ Model training complete. Saved as {model_path}")


if __name__ == "__main__":
    train_churn_model()
