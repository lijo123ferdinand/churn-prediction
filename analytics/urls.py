from django.urls import path
from . import views

urlpatterns = [
    # Dashboard view (e.g., HTML template)
    path('churn-dashboard/', views.churn_dashboard, name='churn_dashboard'),

    # API endpoint (JSON response)
    path('api/churn/<int:user_id>/', views.churn_score, name='churn_score'),
]
