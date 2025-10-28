import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import joblib
import sys
import os
import django
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
# --- Set up Django environment ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "churn_prediction.settings")
django.setup()
from analytics.utils import get_user_features

df = get_user_features()
df['churn'] = (df['days_since_last_login'] > 30).astype(int)

X = df[['days_since_last_login', 'avg_order_value', 'purchase_frequency']]
y = df['churn']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# model = LogisticRegression()
# model = RandomForestClassifier(
#     n_estimators=100,   # number of trees
#     max_depth=5,        # control overfitting
#     random_state=42
# )
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
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))

joblib.dump(model, 'churn_model.pkl')
print("Model saved as churn_model.pkl")
