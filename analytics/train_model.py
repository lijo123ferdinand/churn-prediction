import os
import sys
import django
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.linear_model import SGDClassifier
import joblib

# --- Django setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "churn_prediction.settings")
django.setup()

from analytics.utils import get_user_features


def train_churn_model():
    """
    Incrementally train churn prediction model using user feature data.
    If a previous model exists, it will be loaded and updated (partial_fit).
    Otherwise, a new model will be created and trained from scratch.
    """

    print("🚀 Starting (incremental) churn model training...")

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

    # Define model save path
    model_path = os.path.join(BASE_DIR, "analytics", "churn_model.pkl")

    # --- Incremental Learning Logic ---
    if os.path.exists(model_path):
        print("♻️ Existing model found. Updating with new data (partial_fit)...")
        model = joblib.load(model_path)

        # Safety check: ensure model supports partial_fit
        if hasattr(model, "partial_fit"):
            model.partial_fit(X, y)
        else:
            print("⚠️ Existing model does not support incremental learning. Retraining from scratch.")
            model = SGDClassifier(loss='log_loss', random_state=42)
            model.partial_fit(X, y, classes=[0, 1])
    else:
        print("🆕 No existing model found. Creating a new one...")
        model = SGDClassifier(loss='log_loss', random_state=42)
        model.partial_fit(X, y, classes=[0, 1])

    # Optional: Evaluate model on a small test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    y_pred = model.predict(X_test)
    print("📊 Classification Report:")
    print(classification_report(y_test, y_pred))

    # Save model
    joblib.dump(model, model_path)
    print(f"✅ Model training complete. Saved as {model_path}")

    # --- Auto run churn prediction after training ---
    try:
        from analytics.predict_churn import predict_churn
        print("🔮 Running churn prediction for all users...")
        predict_churn()
    except Exception as e:
        print(f"⚠️ Failed to run churn prediction automatically: {e}")


if __name__ == "__main__":
    train_churn_model()
