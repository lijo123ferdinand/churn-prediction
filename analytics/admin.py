from django.contrib import admin
from .models import UserEvent
from .models import SMTPConfiguration

@admin.register(UserEvent)
class UserEventAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'event_name', 'timestamp')
    list_filter = ('event_name', 'timestamp')
    search_fields = ('user_id', 'event_name')

@admin.register(SMTPConfiguration)
class SMTPConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        'smtp_client_name',
        'smtp_email_host',
        'smtp_email_host_user',
        'aws_region',
        'email_type',
    )
    search_fields = ('smtp_client_name', 'smtp_email_host_user')