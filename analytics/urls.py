from django.urls import path
from . import views
from .api import get_smtp_config

urlpatterns = [
    # Dashboard view (e.g., HTML template)
    path('churn-dashboard/', views.churn_dashboard, name='churn_dashboard'),
    path("smtp-config/", get_smtp_config, name="smtp-config"),

    # API endpoint (JSON response)
    path('api/churn/<int:user_id>/', views.churn_score, name='churn_score'),
]
