from django.urls import path
from . import views

urlpatterns = [
    path('churn-dashboard/', views.churn_dashboard, name='churn_dashboard'),
]
