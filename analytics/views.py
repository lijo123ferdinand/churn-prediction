import os
import sys
import django
import redis
import logging
from django.shortcuts import render
from django.http import JsonResponse
from users.models import User

# --- Logging setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- Django setup (only needed if run standalone) ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "churn_prediction.settings")
django.setup()

# --- Redis connection ---
try:
    r = redis.Redis(host="localhost", port=6379, db=0)
    r.ping()
    logger.info("✅ Connected to Redis successfully.")
except Exception as e:
    logger.error(f"❌ Redis connection failed: {e}")
    r = None


def churn_dashboard(request):
    """Dashboard combining User data + Redis churn score."""
    users_data = []

    if not r:
        logger.error("❌ No Redis connection available.")
        return JsonResponse({"error": "Redis not connected"}, status=500)

    logger.info("📊 Fetching users and Redis churn scores...")

    for user in User.objects.all().order_by("-last_login"):
        redis_key = f"user:{user.id}"
        redis_data = r.hgetall(redis_key)

        logger.info(f"🔍 Checking Redis for key={redis_key} → {redis_data}")

        if redis_data:
            churn_score_raw = redis_data.get(b"churn_score", b"0")
            churn_score = float(churn_score_raw.decode())
            risk_level = "high" if churn_score > 0.7 else "low"
        else:
            churn_score = None
            risk_level = "unknown"

        users_data.append({
            "id": user.id,
            "email": user.email,
            "last_login": str(user.last_login),
            "churn_score": churn_score,
            "risk_level": risk_level
        })

    logger.info(f"✅ Final dashboard data: {users_data}")

    return render(request, "analytics/churn_dashboard.html", {"users": users_data})


def churn_score(request, user_id):
    """API endpoint for real-time churn score."""
    if not r:
        return JsonResponse({"error": "Redis not connected"}, status=500)

    key = f"user:{user_id}"
    logger.info(f"🔍 Fetching Redis data for {key}")
    data = r.hgetall(key)

    if not data:
        logger.warning(f"⚠️ No data found in Redis for {key}")
        return JsonResponse({"error": "User not found"}, status=404)

    result = {k.decode(): v.decode() for k, v in data.items()}
    logger.info(f"📦 Redis raw data for {key}: {result}")

    try:
        result["churn_score"] = float(result["churn_score"])
        result["risk_level"] = "high" if result["churn_score"] > 0.7 else "low"
    except Exception as e:
        logger.error(f"⚠️ Error parsing churn_score for {key}: {e}")
        result["churn_score"] = None
        result["risk_level"] = "unknown"

    return JsonResponse(result)
