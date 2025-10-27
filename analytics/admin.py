from django.contrib import admin
from .models import UserEvent

@admin.register(UserEvent)
class UserEventAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'event_name', 'timestamp')
    list_filter = ('event_name', 'timestamp')
    search_fields = ('user_id', 'event_name')
