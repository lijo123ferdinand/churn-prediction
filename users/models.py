from django.db import models
from django.utils import timezone

class User(models.Model):
    email = models.EmailField(unique=True)
    signup_date = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    total_orders = models.IntegerField(default=0)
    total_spent = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)
    churn_score = models.FloatField(null=True, blank=True)


    def __str__(self):
        return self.email
