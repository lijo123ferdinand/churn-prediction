import os
import sys
import django

# --- Fix BASE_DIR and Django setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "churn_prediction.settings")
django.setup()

from django.shortcuts import render
from users.models import User

def churn_dashboard(request):
    """
    Renders a simple dashboard of users with churn scores.
    """
    users = User.objects.all().order_by('-last_login')  # latest login first
    print(BASE_DIR)
    return render(request, 'analytics/churn_dashboard.html', {'users': users})
