from django.contrib import admin
from django.db.models import Sum

from .models import AlisaUser


@admin.register(AlisaUser)
class AlisaUserAdmin(admin.ModelAdmin):
    """Пользователи Алисы."""
    list_display = ('user', 'parameters', 'last_update', 'action_count',
                    'total_action_count', 'schedule_count', 'total_schedule_count')

    def total_action_count(self, obj):
        return AlisaUser.objects.aggregate(Sum('action_count'))['action_count__sum']
    total_action_count.short_description = 'Total Action Count'

    def total_schedule_count(self, obj):
        return AlisaUser.objects.aggregate(Sum('schedule_count'))['schedule_count__sum']
    total_schedule_count.short_description = 'Total Schedule Count'

