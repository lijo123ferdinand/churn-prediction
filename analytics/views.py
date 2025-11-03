# analytics/views.py
import os
import sys
import django
import redis
from django.shortcuts import render
from django.http import JsonResponse
from users.models import User

# --- Django setup (optional if already configured in manage.py context) ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "churn_prediction.settings")
django.setup()

# --- Redis connection ---
r = redis.Redis(host="localhost", port=6379, db=0)


def churn_dashboard(request):
    """Dashboard combining User data + Redis churn score."""
    users_data = []

    for user in User.objects.all().order_by('-last_login'):
        redis_key = f"user:{user.id}"
        redis_data = r.hgetall(redis_key)

        if redis_data:
            churn_score = float(redis_data.get(b"churn_score", b"0"))
            risk_level = "high" if churn_score > 0.7 else "low"
        else:
            churn_score = None
            risk_level = "unknown"

        users_data.append({
            "id": user.id,
            "email": user.email,
            "last_login": user.last_login,
            "churn_score": churn_score,
            "risk_level": risk_level
        })

    return render(request, "analytics/churn_dashboard.html", {"users": users_data})


def churn_score(request, user_id):
    """API endpoint for real-time churn score."""
    key = f"user:{user_id}"
    data = r.hgetall(key)
    if not data:
        return JsonResponse({"error": "User not found"}, status=404)

    result = {k.decode(): v.decode() for k, v in data.items()}
    result["churn_score"] = float(result["churn_score"])
    result["risk_level"] = "high" if result["churn_score"] > 0.7 else "low"
    return JsonResponse(result)
