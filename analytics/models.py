from django.db import models

# Create your models here.

class UserEvent(models.Model):
    user_id = models.CharField(max_length=100)
    event_name = models.CharField(max_length=100)
    properties = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField()

    def __str__(self):
        return f"{self.user_id} - {self.event_name}"