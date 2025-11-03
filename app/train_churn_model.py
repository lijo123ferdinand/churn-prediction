# train_churn_model.py
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import joblib

# --- Example synthetic training data ---
data = pd.DataFrame({
    "event_count": [2, 5, 8, 1, 15, 7, 3, 20],
    "avg_time_diff_hours": [48, 12, 3, 72, 2, 10, 30, 1],
    "label": [1, 0, 0, 1, 0, 0, 1, 0],  # 1 = churned, 0 = active
})

X = data[["event_count", "avg_time_diff_hours"]]
y = data["label"]

# --- Train model ---
model = Pipeline([
    ("scaler", StandardScaler()),
    ("clf", LogisticRegression())
])
model.fit(X, y)

# --- Save model ---
joblib.dump(model, "churn_model.joblib")
print("✅ Model saved to churn_model.joblib")

