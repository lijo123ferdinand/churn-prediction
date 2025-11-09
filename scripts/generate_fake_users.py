# analytics/generate_fake_users.py
import random
from datetime import datetime, timedelta
import sys
import os
import django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
# --- Set up Django environment ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "churn_prediction.settings")
django.setup()

from users.models import User

for i in range(100):  # adjust the number of fake users
    signup_date = datetime.now() - timedelta(days=random.randint(30, 365))
    last_login = signup_date + timedelta(days=random.randint(0, 300))
    total_orders = random.randint(0, 20)
    total_spent = round(random.uniform(10, 5000), 2)
    email = f"user{i}@example.com"

    if User.objects.filter(email=email).exists():
        continue  # skip existing
    User.objects.create(
        email=f"user{i}@example.com",
        signup_date=signup_date,
        last_login=last_login,
        total_orders=total_orders,
        total_spent=total_spent,
        is_active=True,
        churn_score=None
    )

print("✅ Fake users created successfully!")