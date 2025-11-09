# analytics/train_cart_model.py
import os
import sys
import django
import joblib
from sklearn.linear_model import SGDClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "churn_prediction.settings")
django.setup()

from analytics.utils_cart import get_cart_training_frame

# ✅ Model path in organized structure
MODEL_DIR = os.path.join(BASE_DIR, "ml", "models", "shared_models")
MODEL_PATH = os.path.join(MODEL_DIR, "cart_model.joblib")

def train_cart_model():
    print("🚀 Training CART ABANDONMENT model (local mode)...")

    df = get_cart_training_frame()
    if df.empty:
        print("⚠️ No data available.")
        return

    feature_cols = ["cart_events", "items_added", "cart_value_sum", "had_checkout"]
    X = df[feature_cols]
    y = df["abandoned"]

    if os.path.exists(MODEL_PATH):
        print(f"♻️ Updating existing model: {MODEL_PATH}")
        model = joblib.load(MODEL_PATH)
        model.partial_fit(X, y, classes=[0, 1])
    else:
        print("🆕 Creating new model...")
        model = SGDClassifier(loss="log_loss", random_state=42)
        model.partial_fit(X, y, classes=[0, 1])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    preds = model.predict(X_test)
    print("📊 Classification Report:")
    print(classification_report(y_test, preds))

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"✅ Saved model at {MODEL_PATH}")

if __name__ == "__main__":
    train_cart_model()
