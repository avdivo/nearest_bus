from django.contrib import admin
from django.db.models import Sum

from .models import BotUser, Parameter, IdsForName


@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    """Пользователи в Админке"""
    list_display = ('user_name', 'user_login', 'user_id', 'last_update', 'action_count',
                    'total_action_count', 'schedule_count', 'total_schedule_count')
    search_fields = ['user_name', 'user_login', 'user_id']
    list_filter = ('user_menu',)

    def total_action_count(self, obj):
        return BotUser.objects.aggregate(Sum('action_count'))['action_count__sum']
    total_action_count.short_description = 'Total Action Count'

    def total_schedule_count(self, obj):
        return BotUser.objects.aggregate(Sum('schedule_count'))['schedule_count__sum']
    total_schedule_count.short_description = 'Total Schedule Count'


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """Параметры в Админке"""
    list_display = ('class_name', 'favorites', 'addition', 'bot_user')
    search_fields = ['class_name', 'bot_user']


@admin.register(IdsForName)
class IdsForNameAdmin(admin.ModelAdmin):
    """Идентификаторы в Админке"""
    list_display = ('name', 'id')
