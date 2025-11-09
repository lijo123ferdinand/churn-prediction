import joblib
import sys
import os
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
# --- Set up Django environment ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "churn_prediction.settings")
django.setup()
from analytics.utils import get_user_features
from users.models import User

model = joblib.load('churn_model.pkl')
df = get_user_features()
df['churn_probability'] = model.predict_proba(df[['days_since_last_login', 'avg_order_value', 'purchase_frequency']])[:,1]

for index, row in df.iterrows():
    user = User.objects.get(id=row['user_id'])
    user.churn_score = float(row['churn_probability'])
    user.is_active = row['churn_probability'] < 0.5
    user.save()

print("Predicted and updated the table")
