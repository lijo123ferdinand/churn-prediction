from django.db import models
from users.models import User

# Create your models here.

class UserEvent(models.Model):
    user_id = models.CharField(max_length=100)
    event_name = models.CharField(max_length=100)
    properties = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField()

    def __str__(self):
        return f"{self.user_id} - {self.event_name}"

class SMTPConfiguration(models.Model):
    smtp_client_name = models.CharField(max_length=50, unique=True)
    smtp_email_host = models.CharField(max_length=255)
    smtp_email_use_tls = models.BooleanField(default=True)
    smtp_email_port = models.IntegerField(default=587)
    smtp_email_host_user = models.CharField(max_length=255)
    smtp_email_host_password = models.CharField(max_length=255)
    access_key_id = models.CharField(max_length=255, blank=True, null=True)
    aws_secret_key = models.CharField(max_length=255, blank=True, null=True)
    aws_region = models.CharField(max_length=50, blank=True, null=True)
    email_type = models.CharField(max_length=50, default="SMTP")

    def __str__(self):
        return self.smtp_client_name

class CartEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart_event_logs")
    event_name = models.CharField(max_length=100)
    properties = models.JSONField(default=dict)
    timestamp = models.DateTimeField()

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user_id} - {self.event_name} @ {self.timestamp}"